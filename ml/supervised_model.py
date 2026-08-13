"""
Supervised model: predicts whether the user will hit their weekly study
goal, using ONLY the previous week's features (see ml/preprocessing.py
for the leakage-avoidance logic).

CRITICAL METHODOLOGY NOTE — chronological splitting:
This is a time-series prediction problem. Using sklearn's default
train_test_split() would randomly shuffle weeks, meaning the model could
be "tested" on week 3 after having "trained" on week 10 — testing on the
past using information from the future, which silently inflates apparent
accuracy and doesn't reflect the real prediction task (predicting an
UPCOMING week). This module instead sorts weeks chronologically and
splits by date: the earliest weeks are always the training set, the most
recent weeks are always the test set. This is slower to reach "good"
metrics on small datasets (there's no way to get lucky with a favorable
random split) but is the only honest way to evaluate this kind of model.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
)

from config import MIN_WEEKS_FOR_SUPERVISED_EVAL

FEATURE_COLS = [
    "prev_study_minutes", "prev_avg_calories", "prev_workout_minutes",
    "prev_avg_sleep_hours", "prev_total_expense", "prev_task_completion_rate",
]


def chronological_split(weekly_df: pd.DataFrame, test_weeks: int = 2):
    """
    Splits weekly_df (already sorted by week ascending from preprocessing)
    into train/test WITHOUT shuffling. The last `test_weeks` rows become
    the test set (the most recent, "future" weeks); everything before
    that is training data. This is the only split direction that makes
    sense for a forecast — training must always precede testing in time.
    """
    weekly_df = weekly_df.sort_values("week").reset_index(drop=True)
    if len(weekly_df) <= test_weeks:
        return weekly_df, pd.DataFrame(columns=weekly_df.columns)
    train = weekly_df.iloc[:-test_weeks]
    test = weekly_df.iloc[-test_weeks:]
    return train, test


def train_supervised_model(weekly_df: pd.DataFrame) -> dict:
    """
    Trains a LogisticRegression classifier using a CHRONOLOGICAL split.

    If there isn't enough data for a meaningful chronological evaluation
    (see MIN_WEEKS_FOR_SUPERVISED_EVAL), trains on everything available
    and explicitly reports that no reliable held-out evaluation was
    possible — rather than reporting a metric computed on 1-2 test points,
    which would be statistically meaningless.
    """
    if weekly_df.empty or len(weekly_df) < 3:
        return {
            "model": None, "scaler": None, "status": "insufficient_data",
            "message": f"Only {len(weekly_df)} labeled week(s) available. "
                       "Need at least 3 to train even a toy model — keep logging data.",
            "n_samples": len(weekly_df),
        }

    weekly_df = weekly_df.sort_values("week").reset_index(drop=True)

    if len(weekly_df) >= MIN_WEEKS_FOR_SUPERVISED_EVAL:
        test_weeks = max(2, round(len(weekly_df) * 0.25))
        train_df, test_df = chronological_split(weekly_df, test_weeks=test_weeks)

        X_train = train_df[FEATURE_COLS].values
        y_train = train_df["goal_hit"].values
        X_test = test_df[FEATURE_COLS].values
        y_test = test_df["goal_hit"].values

        if len(set(y_train)) < 2:
            # All training weeks have the same label — a binary classifier
            # literally cannot be fit (sklearn raises on single-class data).
            # Report this as a genuine no-model state rather than forcing
            # a fit that would error, or silently fitting something meaningless.
            return {
                "model": None, "scaler": None, "status": "trained_no_eval",
                "message": "All training weeks have the same outcome (goal always hit or "
                           "always missed) — can't fit a classifier without both outcomes "
                           "represented in the data yet. Keep logging varied weeks.",
                "n_samples": len(weekly_df), "n_train": len(train_df), "n_test": len(test_df),
            }

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = LogisticRegression(max_iter=1000)
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)

        cm = confusion_matrix(y_test, y_pred, labels=[0, 1]).tolist()

        return {
            "model": model, "scaler": scaler, "status": "evaluated",
            "accuracy": round(accuracy_score(y_test, y_pred), 3),
            "precision": round(precision_score(y_test, y_pred, zero_division=0), 3),
            "recall": round(recall_score(y_test, y_pred, zero_division=0), 3),
            "f1_score": round(f1_score(y_test, y_pred, zero_division=0), 3),
            "confusion_matrix": cm,
            "classification_report": classification_report(y_test, y_pred, zero_division=0),
            "n_samples": len(weekly_df), "n_train": len(train_df), "n_test": len(test_df),
            "train_class_distribution": {int(k): int(v) for k, v in pd.Series(y_train).value_counts().items()},
            "test_class_distribution": {int(k): int(v) for k, v in pd.Series(y_test).value_counts().items()},
            "split_method": "chronological",
        }

    # Not enough weeks for a trustworthy chronological test split —
    # train on everything, evaluate nothing, say so explicitly.
    X = weekly_df[FEATURE_COLS].values
    y = weekly_df["goal_hit"].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    if len(set(y)) < 2:
        return {
            "model": None, "scaler": None, "status": "trained_no_eval",
            "message": "All available weeks have the same outcome (goal always hit or "
                       "always missed) — not enough variation yet to fit a classifier. "
                       "Keep logging — this resolves itself once you have a mixed history.",
            "n_samples": len(weekly_df),
        }

    model = LogisticRegression(max_iter=1000)
    model.fit(X_scaled, y)

    return {
        "model": model, "scaler": scaler, "status": "trained_no_eval",
        "message": f"Trained on all {len(weekly_df)} available week(s), but that's fewer than "
                   f"the {MIN_WEEKS_FOR_SUPERVISED_EVAL} weeks needed for a trustworthy "
                   "chronological train/test split. Keep logging — evaluation metrics will "
                   "appear automatically once enough weeks of history exist.",
        "n_samples": len(weekly_df),
    }


def predict_next_week(model_bundle: dict, latest_week_features: dict) -> dict:
    """Predicts NEXT week's goal outcome from this week's raw feature values."""
    if model_bundle["model"] is None:
        return {"prediction": None, "probability": None,
                "message": model_bundle.get("message", "Model not trained.")}

    row = np.array([[latest_week_features[c.replace("prev_", "")] for c in FEATURE_COLS]])
    row_scaled = model_bundle["scaler"].transform(row)

    model = model_bundle["model"]
    pred = model.predict(row_scaled)[0]
    proba = model.predict_proba(row_scaled)[0][1]

    return {"prediction": int(pred), "probability": round(float(proba), 3)}


def explain_coefficients(model_bundle: dict) -> pd.DataFrame:
    """
    Returns feature coefficients for interpretability. Labeled as
    "important predictive features", never as causal relationships.
    """
    if model_bundle["model"] is None:
        return pd.DataFrame()

    coefs = model_bundle["model"].coef_[0]
    return pd.DataFrame({
        "feature": FEATURE_COLS, "coefficient": coefs,
    }).sort_values("coefficient", key=abs, ascending=False).reset_index(drop=True)
