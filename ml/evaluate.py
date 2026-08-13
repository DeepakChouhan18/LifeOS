"""
Evaluation summary helpers — pull the relevant fields out of model
bundles / stored metadata into short, honest, human-readable strings.
"""

import json


def summarize_supervised(bundle: dict) -> str:
    if bundle["status"] == "evaluated":
        return (
            f"Accuracy: {bundle['accuracy']} · Precision: {bundle['precision']} · "
            f"Recall: {bundle['recall']} · F1: {bundle['f1_score']} "
            f"(chronological split — trained on {bundle['n_train']} weeks, "
            f"tested on the {bundle['n_test']} most recent weeks)"
        )
    elif bundle["status"] == "trained_no_eval":
        return bundle["message"]
    else:
        return bundle.get("message", "Model not trained.")


def summarize_clustering(bundle: dict) -> str:
    if bundle["status"] == "clustered":
        return (
            f"Found {bundle['k']} clusters (silhouette score: {bundle['silhouette_score']}, "
            f"range -1 to 1, higher = more distinct clusters)."
        )
    return bundle.get("message", "Clustering not available.")


def summarize_metadata(meta) -> str:
    """Summarizes a stored MLModelMetadata row for 'last trained on X' display."""
    if meta is None:
        return "Not trained yet."

    metrics = {}
    if meta.metrics_json:
        try:
            metrics = json.loads(meta.metrics_json)
        except (json.JSONDecodeError, TypeError):
            pass

    trained_str = meta.trained_at.strftime("%b %d, %Y %H:%M") if meta.trained_at else "unknown time"
    parts = [f"Last trained: {trained_str}", f"Samples: {meta.n_samples or 0}"]
    if meta.data_period_start and meta.data_period_end:
        parts.append(f"Data period: {meta.data_period_start} to {meta.data_period_end}")
    if metrics.get("accuracy") is not None:
        parts.append(f"Accuracy: {metrics['accuracy']}")
    if metrics.get("silhouette_score") is not None:
        parts.append(f"Silhouette: {metrics['silhouette_score']}")
    return " · ".join(parts)
