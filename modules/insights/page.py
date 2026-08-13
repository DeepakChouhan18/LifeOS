"""
Streamlit UI for Insights: cross-domain analytics + Machine Learning.

IMPORTANT: models are NOT retrained on every page load (see spec on ML
training architecture). Training only happens when the user clicks
"Train Models". Between training runs, this page reads the last stored
result from st.session_state (within the session) and MLModelMetadata
(across sessions/restarts), so re-opening Insights doesn't imply retraining.
"""

import streamlit as st
import plotly.express as px
import pandas as pd

from database.connection import get_session
from database import raw_queries as rq
from ml import preprocessing, train as ml_train
from ml.supervised_model import explain_coefficients
from ml.unsupervised_model import describe_clusters, label_clusters
from ml.evaluate import summarize_supervised, summarize_clustering, summarize_metadata
from utils import ui_components
from config import DEFAULT_USER_ID


def render():
    ui_components.page_header("🔍 Insights", "Cross-domain patterns and machine learning, trained on your own data.")

    db = get_session()
    try:
        tab_cross, tab_ml = st.tabs(["🔗 Cross-Domain Patterns", "🤖 Machine Learning"])

        with tab_cross:
            _render_cross_domain_tab(db)

        with tab_ml:
            _render_ml_tab(db)
    finally:
        db.close()


def _render_cross_domain_tab(db):
    st.subheader("Cross-Domain Relationships")
    st.caption(
        "These show **observed patterns** in your own logged data — not causation. "
        "A pattern here doesn't mean one thing caused the other."
    )

    cross_df = pd.DataFrame(rq.get_cross_study_workout(db, DEFAULT_USER_ID))
    if not cross_df.empty and len(cross_df) >= 2:
        st.markdown("##### Study Hours vs. Workout Frequency (by week)")
        fig = px.scatter(
            cross_df, x="study_hours", y="workout_count", size="workout_minutes",
            color="week", title="Weekly study hours vs. workouts completed",
            labels={"study_hours": "Study Hours", "workout_count": "Workouts"},
        )
        st.plotly_chart(fig, use_container_width=True, key="insights_cross_scatter")
    else:
        ui_components.empty_state("Log at least 2 weeks of study and workout data to see this pattern.")

    st.divider()
    st.markdown("##### Spending by Weekday")
    weekday_df = pd.DataFrame(rq.get_spending_by_weekday(db, DEFAULT_USER_ID))
    if not weekday_df.empty:
        fig = px.bar(weekday_df, x="weekday_name", y="total_spent", title="Total spend by day of week")
        st.plotly_chart(fig, use_container_width=True, key="insights_weekday_spend")
    else:
        ui_components.empty_state("No expense data yet.")


def _render_ml_tab(db):
    st.subheader("Machine Learning")
    st.caption(
        "Models train on-demand, not automatically — click **Train Models** below "
        "whenever you want fresh predictions from your latest data."
    )

    if st.button("🔄 Train Models", type="primary"):
        with st.spinner("Building features and training models..."):
            result = ml_train.run_training(db, DEFAULT_USER_ID)
            st.session_state["ml_result"] = result
        st.success("Training complete.")

    result = st.session_state.get("ml_result")

    supervised_meta = ml_train.get_latest_metadata(db, DEFAULT_USER_ID, "supervised")
    cluster_meta = ml_train.get_latest_metadata(db, DEFAULT_USER_ID, "unsupervised")

    st.divider()
    st.markdown("### 📈 Supervised: Weekly Study Goal Prediction")
    st.caption(
        "Logistic Regression predicts whether you'll hit your weekly study goal, "
        "using only the PREVIOUS week's study/health/finance/task stats — never "
        "the current week's own data (would be circular). Evaluated with a "
        "**chronological** train/test split (earliest weeks train, most recent weeks test) "
        "— never a random shuffle, since this is a forecasting problem."
    )

    if supervised_meta:
        st.caption(summarize_metadata(supervised_meta))

    if result and result["supervised"]["model"] is not None:
        bundle = result["supervised"]
        st.info(summarize_supervised(bundle))

        if bundle["status"] == "evaluated":
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Confusion Matrix** (rows=actual, cols=predicted)")
                cm_df = pd.DataFrame(bundle["confusion_matrix"],
                                      index=["Actual: Missed", "Actual: Hit"],
                                      columns=["Pred: Missed", "Pred: Hit"])
                st.dataframe(cm_df, use_container_width=True)
            with c2:
                st.write("**Class Distribution**")
                st.write(f"Train: {bundle['train_class_distribution']}")
                st.write(f"Test: {bundle['test_class_distribution']}")

        coef_df = explain_coefficients(bundle)
        if not coef_df.empty:
            st.write("**Important predictive features** (not causal relationships):")
            fig = px.bar(coef_df, x="feature", y="coefficient",
                         title="Feature coefficients (magnitude = influence on prediction)",
                         color="coefficient", color_continuous_scale="RdBu")
            st.plotly_chart(fig, use_container_width=True, key="insights_coef_bar")
    elif not result:
        ui_components.empty_state("Click 'Train Models' above to generate a prediction.")
    else:
        st.info(summarize_supervised(result["supervised"]))

    st.divider()
    st.markdown("### 🧩 Unsupervised: Day-Type Clustering")
    st.caption(
        "KMeans groups your logged days into behavior types using study, calories, "
        "workout, sleep, and spend together. Cluster labels compare each cluster "
        "against YOUR OWN historical average — not fixed universal thresholds."
    )

    if cluster_meta:
        st.caption(summarize_metadata(cluster_meta))

    if result and result["cluster"]["model"] is not None:
        bundle = result["cluster"]
        st.info(summarize_clustering(bundle))

        labels = label_clusters(bundle)
        for c in labels:
            with st.container():
                st.markdown(f"**🔹 {c['label']}** — {c['day_count']} days")
                char_str = " · ".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in c["characteristics"].items())
                st.caption(char_str)

        labeled_df = bundle["labeled_df"]
        fig = px.scatter(
            labeled_df, x="study_minutes", y="calories", color=labeled_df["cluster"].astype(str),
            title="Days by cluster: study minutes vs. calories",
            labels={"color": "Cluster"}, hover_data=["workout_minutes", "expense_amount", "sleep_hours"],
        )
        st.plotly_chart(fig, use_container_width=True, key="insights_cluster_scatter")
    elif not result:
        ui_components.empty_state("Click 'Train Models' above to see your day-type clusters.")
    else:
        st.info(summarize_clustering(result["cluster"]))
