"""
Training workflow — builds features, trains both models, saves model
artifacts (joblib) AND training metadata (database.models.MLModelMetadata).

Deliberately a SEPARATE step from viewing the Insights page (see
ml/page.py's "Train Models" button) — the app does not silently retrain
on every page load. run_training() is the single entry point used by
both the CLI (`python ml/train.py`) and the Streamlit "Train Models" button.
"""

import os
import sys
import json
import joblib
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_session
from database.models import MLModelMetadata
from modules.settings import crud as settings_crud
from config import DEFAULT_USER_ID, ML_MODELS_DIR
from ml import preprocessing
from ml.supervised_model import train_supervised_model, FEATURE_COLS as SUPERVISED_FEATURES
from ml.unsupervised_model import train_clustering_model, FEATURE_COLS as CLUSTER_FEATURES


def _save_metadata(session, user_id, model_type, algorithm, bundle, feature_names, data_period):
    metrics = {k: v for k, v in bundle.items() if k not in ("model", "scaler", "labeled_df", "message")}
    # Drop non-JSON-serializable objects (numpy arrays inside confusion_matrix are already .tolist()'d)
    metrics_clean = {}
    for k, v in metrics.items():
        try:
            json.dumps(v)
            metrics_clean[k] = v
        except (TypeError, ValueError):
            pass

    meta = MLModelMetadata(
        user_id=user_id, model_type=model_type, algorithm=algorithm,
        n_samples=bundle.get("n_samples"), n_features=len(feature_names),
        feature_names=",".join(feature_names),
        data_period_start=data_period[0], data_period_end=data_period[1],
        metrics_json=json.dumps(metrics_clean),
        status=bundle["status"],
    )
    session.add(meta)
    session.commit()
    return meta


def run_training(session, user_id: int = DEFAULT_USER_ID) -> dict:
    """
    Runs the full training workflow for both models and persists results.
    Returns a summary dict the UI can display immediately without a
    separate DB read.
    """
    os.makedirs(ML_MODELS_DIR, exist_ok=True)

    profile = settings_crud.get_user_profile(session, user_id)
    weekly_goal_minutes = (profile.daily_study_goal_minutes * 7) if profile else None

    daily_df = preprocessing.build_daily_features_df(session, user_id)
    weekly_df = preprocessing.build_weekly_features_df(session, user_id, weekly_goal_minutes)

    data_period = (None, None)
    if not daily_df.empty:
        data_period = (daily_df["log_date"].min().date(), daily_df["log_date"].max().date())

    supervised_bundle = train_supervised_model(weekly_df)
    cluster_bundle = train_clustering_model(daily_df)

    # Persist artifacts (only if a model was actually fit)
    if supervised_bundle["model"] is not None:
        joblib.dump(
            {"model": supervised_bundle["model"], "scaler": supervised_bundle["scaler"]},
            os.path.join(ML_MODELS_DIR, f"supervised_model_{user_id}.pkl"),
        )
    if cluster_bundle["model"] is not None:
        joblib.dump(
            {"model": cluster_bundle["model"], "scaler": cluster_bundle["scaler"]},
            os.path.join(ML_MODELS_DIR, f"cluster_model_{user_id}.pkl"),
        )

    _save_metadata(session, user_id, "supervised", "LogisticRegression",
                    supervised_bundle, SUPERVISED_FEATURES, data_period)
    _save_metadata(session, user_id, "unsupervised", "KMeans",
                    cluster_bundle, CLUSTER_FEATURES, data_period)

    return {
        "supervised": supervised_bundle, "cluster": cluster_bundle,
        "daily_df": daily_df, "weekly_df": weekly_df,
    }


def get_latest_metadata(session, user_id: int, model_type: str):
    """Returns the most recent training run's metadata for display, without retraining."""
    return (
        session.query(MLModelMetadata)
        .filter_by(user_id=user_id, model_type=model_type)
        .order_by(MLModelMetadata.trained_at.desc())
        .first()
    )


if __name__ == "__main__":
    db = get_session()
    try:
        print("Running training workflow...")
        result = run_training(db, DEFAULT_USER_ID)
        print(f"Supervised status: {result['supervised']['status']}")
        print(f"Clustering status: {result['cluster']['status']}")
        print(f"Saved artifacts to {ML_MODELS_DIR}/")
    finally:
        db.close()
