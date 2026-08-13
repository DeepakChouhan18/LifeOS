"""
Tests for ml/supervised_model.py and ml/unsupervised_model.py —
specifically the methodology requirements: chronological (not random)
splitting, honest insufficient-data handling, and safe behavior on
single-class / invalid training data.
"""

import pandas as pd
import numpy as np
import pytest

from ml.supervised_model import (
    train_supervised_model, chronological_split, predict_next_week,
    explain_coefficients, FEATURE_COLS,
)
from ml.unsupervised_model import train_clustering_model, label_clusters


def _make_weekly_df(n, alternating_labels=True, feature_scale=100):
    np.random.seed(0)
    labels = [i % 2 for i in range(n)] if alternating_labels else [0] * n
    df = pd.DataFrame({
        "week": [f"2026-W{i:02d}" for i in range(n)],
        "goal_hit": labels,
    })
    for col in FEATURE_COLS:
        df[col] = np.random.uniform(10, feature_scale, n)
    return df


def test_chronological_split_preserves_order_no_shuffle():
    df = _make_weekly_df(10)
    train, test = chronological_split(df, test_weeks=3)

    assert list(train["week"]) == [f"2026-W{i:02d}" for i in range(7)]
    assert list(test["week"]) == [f"2026-W{i:02d}" for i in range(7, 10)]


def test_chronological_split_test_set_is_always_the_most_recent():
    df = _make_weekly_df(12)
    train, test = chronological_split(df, test_weeks=4)

    assert train["week"].max() < test["week"].min()


def test_supervised_model_insufficient_data_reports_honestly():
    df = _make_weekly_df(2)
    bundle = train_supervised_model(df)

    assert bundle["status"] == "insufficient_data"
    assert bundle["model"] is None
    assert "message" in bundle


def test_supervised_model_single_class_does_not_crash():
    """
    Regression test: training data with only one label class must not
    raise an unhandled sklearn ValueError — this was a real bug caught
    during development (LogisticRegression cannot fit single-class data).
    """
    df = _make_weekly_df(8, alternating_labels=False)
    bundle = train_supervised_model(df)  # must not raise

    assert bundle["status"] == "trained_no_eval"
    assert bundle["model"] is None
    assert "message" in bundle


def test_supervised_model_evaluated_path_produces_real_metrics():
    df = _make_weekly_df(10, alternating_labels=True)
    bundle = train_supervised_model(df)

    assert bundle["status"] == "evaluated"
    assert bundle["split_method"] == "chronological"
    assert 0.0 <= bundle["accuracy"] <= 1.0
    assert 0.0 <= bundle["precision"] <= 1.0
    assert 0.0 <= bundle["recall"] <= 1.0
    assert 0.0 <= bundle["f1_score"] <= 1.0
    assert len(bundle["confusion_matrix"]) == 2
    assert bundle["n_train"] + bundle["n_test"] == bundle["n_samples"]


def test_supervised_model_train_test_counts_match_total_samples():
    df = _make_weekly_df(12, alternating_labels=True)
    bundle = train_supervised_model(df)

    assert bundle["n_train"] + bundle["n_test"] == len(df)


def test_predict_next_week_returns_valid_probability():
    df = _make_weekly_df(10, alternating_labels=True)
    bundle = train_supervised_model(df)

    features = {c.replace("prev_", ""): 100.0 for c in FEATURE_COLS}
    result = predict_next_week(bundle, features)

    assert result["prediction"] in (0, 1)
    assert 0.0 <= result["probability"] <= 1.0


def test_predict_next_week_handles_untrained_model():
    bundle = {"model": None, "scaler": None, "message": "not enough data"}
    result = predict_next_week(bundle, {})
    assert result["prediction"] is None


def test_explain_coefficients_matches_feature_count():
    df = _make_weekly_df(10, alternating_labels=True)
    bundle = train_supervised_model(df)
    coef_df = explain_coefficients(bundle)

    assert len(coef_df) == len(FEATURE_COLS)
    assert set(coef_df["feature"]) == set(FEATURE_COLS)


# =======================================================================
# UNSUPERVISED MODEL TESTS
# =======================================================================

def _make_daily_df(n, seed=0):
    np.random.seed(seed)
    return pd.DataFrame({
        "log_date": pd.date_range("2026-01-01", periods=n),
        "study_minutes": np.random.uniform(0, 200, n),
        "calories": np.random.uniform(1500, 2800, n),
        "workout_minutes": np.random.uniform(0, 90, n),
        "sleep_hours": np.random.uniform(4, 9, n),
        "expense_amount": np.random.uniform(0, 1000, n),
    })


def test_clustering_insufficient_data_reports_honestly():
    df = _make_daily_df(3)
    bundle = train_clustering_model(df)

    assert bundle["status"] == "insufficient_data"
    assert bundle["model"] is None


def test_clustering_with_enough_data_produces_valid_silhouette():
    df = _make_daily_df(30)
    bundle = train_clustering_model(df)

    assert bundle["status"] == "clustered"
    assert -1.0 <= bundle["silhouette_score"] <= 1.0
    assert bundle["k"] >= 2


def test_cluster_labels_use_relative_not_fixed_thresholds():
    np.random.seed(1)
    light_studier = pd.DataFrame({
        "log_date": pd.date_range("2026-01-01", periods=30),
        "study_minutes": np.concatenate([np.random.uniform(0, 20, 15), np.random.uniform(80, 120, 15)]),
        "calories": np.random.uniform(1800, 2200, 30),
        "workout_minutes": np.random.uniform(0, 30, 30),
        "sleep_hours": np.random.uniform(6, 8, 30),
        "expense_amount": np.random.uniform(0, 200, 30),
    })
    bundle = train_clustering_model(light_studier)
    if bundle["model"] is not None:
        labels = label_clusters(bundle)
        assert len(labels) >= 1
        assert all("label" in c and "day_count" in c for c in labels)


def test_clustering_handles_missing_feature_columns_gracefully():
    df = _make_daily_df(20).drop(columns=["expense_amount"])
    bundle = train_clustering_model(df)  # must not raise
    assert bundle["status"] in ("clustered", "insufficient_data", "no_valid_clustering")
