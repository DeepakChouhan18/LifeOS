"""
Streamlit UI for Insights: cross-domain analytics + Machine Learning.

Models train on-demand. Technical metrics and internal model names are kept
in an expander to focus the user experience on plain-language prediction outcomes
and daily cluster patterns.
"""

import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

from database.connection import get_session
from database import raw_queries as rq, cache
from ml import preprocessing, train as ml_train
from modules.settings import crud as settings_crud
from ml.supervised_model import explain_coefficients, predict_next_week
from ml.unsupervised_model import describe_clusters, label_clusters
from ml.evaluate import summarize_supervised, summarize_clustering, summarize_metadata
from utils import ui_components
from utils.charts import apply_chart_theme



def render(user_id: int):
    ui_components.page_header("Insights", "Cross-domain patterns, correlations, and data-driven behavioral forecasts.")

    db = get_session()
    try:
        tab_cross, tab_ml = st.tabs(["Cross-Domain Patterns", "Machine Learning"])

        with tab_cross:
            _render_cross_domain_tab(db, user_id)

        with tab_ml:
            _render_ml_tab(db, user_id)
    finally:
        db.close()


def _render_cross_domain_tab(db, user_id: int):
    ui_components.section_header("Cross-Domain Relationships")
    st.caption(
        "These charts show observed patterns in your logged history. "
        "They represent correlations in your behavior, not causal relationships."
    )

    # Read from cache — these are read-only analytics queries.
    cross_df = pd.DataFrame(cache.get_insights_cross_study_workout(user_id))
    col1, col2 = st.columns(2, gap="large")

    with col1:
        if not cross_df.empty and len(cross_df) >= 2:
            fig = px.scatter(
                cross_df, x="study_hours", y="workout_count", size="workout_minutes",
                color="week", title="Study Hours vs. Workouts",
                labels={"study_hours": "Study Hours", "workout_count": "Workouts Completed", "week": "Week"},
            )
            fig = apply_chart_theme(fig, "Study Hours vs. Workouts")
            st.plotly_chart(fig, use_container_width=True, key="insights_cross_scatter")
        else:
            ui_components.empty_state(
                "Log at least 2 weeks of study and workouts to see this pattern.",
                icon=""
            )

    with col2:
        weekday_df = pd.DataFrame(cache.get_insights_spending_by_weekday(user_id))
        if not weekday_df.empty:
            fig = px.bar(
                weekday_df, x="weekday_name", y="total_spent",
                title="Spending by Weekday",
                labels={"weekday_name": "Day of Week", "total_spent": "Total Spent (₹)"},
                color="total_spent",
                color_continuous_scale="Purples"
            )
            fig.update_layout(showlegend=False, coloraxis_showscale=False)
            fig = apply_chart_theme(fig, "Spending by Weekday")
            st.plotly_chart(fig, use_container_width=True, key="insights_weekday_spend")
        else:
            ui_components.empty_state("No expense logs yet.", icon="")


# Helper to get current week's features for next week prediction
def _get_current_week_features(db, user_id):
    profile = settings_crud.get_user_profile(db, user_id)
    weekly_goal_minutes = (profile.daily_study_goal_minutes * 7) if profile else None
    
    daily = preprocessing.build_daily_features_df(db, user_id)
    if daily.empty:
        return None
    daily["week"] = daily["log_date"].dt.strftime("%Y-%W")
    weekly = daily.groupby("week").agg(
        study_minutes=("study_minutes", "sum"),
        avg_calories=("calories", "mean"),
        workout_minutes=("workout_minutes", "sum"),
        avg_sleep_hours=("sleep_hours", "mean"),
        total_expense=("expense_amount", "sum"),
    ).reset_index()
    
    # task completion
    from sqlalchemy import text
    task_df = pd.read_sql(
        text("SELECT due_date AS log_date, is_completed FROM study_tasks WHERE user_id = :uid AND due_date IS NOT NULL"),
        db.bind, params={"uid": user_id}
    )
    if not task_df.empty:
        task_df["log_date"] = pd.to_datetime(task_df["log_date"])
        task_df["week"] = task_df["log_date"].dt.strftime("%Y-%W")
        completion_by_week = task_df.groupby("week")["is_completed"].mean().reset_index()
        completion_by_week.columns = ["week", "task_completion_rate"]
        weekly = weekly.merge(completion_by_week, on="week", how="left")
    else:
        weekly["task_completion_rate"] = 0
    weekly["task_completion_rate"] = weekly["task_completion_rate"].fillna(0)
    
    if weekly.empty:
        return None
    
    last_row = weekly.iloc[-1]
    return {
        "study_minutes": float(last_row["study_minutes"]),
        "avg_calories": float(last_row["avg_calories"]),
        "workout_minutes": float(last_row["workout_minutes"]),
        "avg_sleep_hours": float(last_row["avg_sleep_hours"]),
        "total_expense": float(last_row["total_expense"]),
        "task_completion_rate": float(last_row["task_completion_rate"]),
    }


def _render_ml_tab(db, user_id: int):
    ui_components.section_header("Machine Learning Insights")
    st.caption(
        "Models train on-demand using your own logged historical data. "
        "Click Train Models below to rebuild predictions using your latest history."
    )

    # Clean action layout
    c_btn, c_info = st.columns([1, 3])
    with c_btn:
        train_triggered = st.button("Train Models", type="primary", use_container_width=True)
    with c_info:
        supervised_meta = ml_train.get_latest_metadata(db, user_id, "supervised")
        if supervised_meta:
            st.markdown(f'<p style="font-size:0.8rem; color:#64748b; margin-top:0.5rem;">{summarize_metadata(supervised_meta)}</p>', unsafe_allow_html=True)

    if train_triggered:
        with st.spinner("Processing data and training models..."):
            result = ml_train.run_training(db, user_id)
            st.session_state["ml_result"] = result
        st.success("Models trained and saved successfully.")
        st.rerun()

    result = st.session_state.get("ml_result")

    # -----------------------------------------------------------------------
    # Supervised: Weekly Study Goal Prediction
    # -----------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    ui_components.section_header("Study Goal Prediction", subtitle="Forecasts whether you will meet your study goal next week based on your activity this week.")

    if result and result["supervised"]["model"] is not None:
        bundle = result["supervised"]
        
        # Make next week prediction using current week's features
        current_features = _get_current_week_features(db, user_id)
        if current_features:
            pred_res = predict_next_week(bundle, current_features)
            if pred_res["prediction"] is not None:
                pred_label = "Likely to hit weekly goal" if pred_res["prediction"] == 1 else "Likely to miss weekly goal"
                banner_variant = "success" if pred_res["prediction"] == 1 else "warning"
                prob_pct = pred_res["probability"] * 100 if pred_res["prediction"] == 1 else (1.0 - pred_res["probability"]) * 100
                ui_components.info_banner(
                    f"**Prediction for next week:** {pred_label} (Confidence: **{prob_pct:.0f}%**)<br>"
                    f"<span style='font-size:0.8rem; opacity:0.85;'>Estimated from your study, tasks, sleep, and fitness levels logged so far this week.</span>",
                    banner_type=banner_variant
                )
        else:
            ui_components.info_banner("Insufficient logged weeks to generate upcoming week prediction.")

        # Collapsible technical section
        with st.expander("Model Details & Evaluation Metrics"):
            st.markdown(f"**Performance Summary:** {summarize_supervised(bundle)}")
            
            if bundle["status"] == "evaluated":
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Confusion Matrix** (actual vs. predicted)")
                    cm_df = pd.DataFrame(bundle["confusion_matrix"],
                                          index=["Actual: Missed", "Actual: Hit"],
                                          columns=["Pred: Missed", "Pred: Hit"])
                    st.dataframe(cm_df, use_container_width=True)
                with c2:
                    st.write("**Data Distribution**")
                    st.write(f"Train set: {bundle['train_class_distribution']} weeks")
                    st.write(f"Test set: {bundle['test_class_distribution']} weeks")

            coef_df = explain_coefficients(bundle)
            if not coef_df.empty:
                st.markdown("<br>**Predictive Weights** (magnitude implies relevance, direction implies positive/negative correlation)", unsafe_allow_html=True)
                # Pretty mapping of feature names for non-technical users
                friendly_names = {
                    "prev_study_minutes": "Study Time",
                    "prev_avg_calories": "Calorie Intake",
                    "prev_workout_minutes": "Workout Duration",
                    "prev_avg_sleep_hours": "Sleep Duration",
                    "prev_total_expense": "Spending Amount",
                    "prev_task_completion_rate": "Task Completion Rate"
                }
                coef_df["feature_name"] = coef_df["feature"].map(friendly_names)
                fig = px.bar(coef_df, x="feature_name", y="coefficient",
                             title="Predictive Weights",
                             labels={"feature_name": "Activity Category", "coefficient": "Relevance Weight"},
                             color="coefficient", color_continuous_scale="RdBu")
                fig.update_layout(showlegend=False, coloraxis_showscale=False)
                fig = apply_chart_theme(fig, "Predictive Weights")
                st.plotly_chart(fig, use_container_width=True, key="insights_coef_bar")
    else:
        ui_components.empty_state("Click 'Train Models' to generate predictions.", icon="")

    # -----------------------------------------------------------------------
    # Unsupervised: Day-Type Clustering
    # -----------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    ui_components.section_header("Behavioral Clusters", subtitle="Groups your historical days into distinct patterns based on combined activities.")

    if result and result["cluster"]["model"] is not None:
        bundle = result["cluster"]
        labels = label_clusters(bundle)

        st.markdown("**Your Day Types:**")
        cols = st.columns(min(3, len(labels)))
        for idx, c in enumerate(labels):
            col = cols[idx % len(cols)]
            with col:
                char_list = [f"• {k.replace('_', ' ').title()}: {v}" for k, v in c["characteristics"].items()]
                char_str = "<br>".join(char_list)
                st.markdown(
                    f'<div style="padding:1rem; background:#111927; border-radius:10px; border:1px solid #1e293b; height:100%;">'
                    f'  <div style="font-weight:700; color:#818cf8; font-size:0.95rem; margin-bottom:0.4rem;">{c["label"]}</div>'
                    f'  <div style="font-size:0.8rem; color:#94a3b8; font-weight:600; margin-bottom:0.6rem;">{c["day_count"]} day(s) matched</div>'
                    f'  <div style="font-size:0.8rem; color:#e2e8f0; line-height:1.4;">{char_str}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("Clustering Diagnostics & Scatter Plot"):
            st.markdown(f"**Diagnostic Summary:** {summarize_clustering(bundle)}")
            
            labeled_df = bundle["labeled_df"]
            fig = px.scatter(
                labeled_df, x="study_minutes", y="calories", color=labeled_df["cluster"].astype(str),
                title="Study Minutes vs. Calories by Cluster",
                labels={"color": "Day Type Cluster", "study_minutes": "Study Minutes", "calories": "Calories (kcal)"},
                hover_data=["workout_minutes", "expense_amount", "sleep_hours"],
            )
            fig = apply_chart_theme(fig, "Study Minutes vs. Calories by Cluster")
            st.plotly_chart(fig, use_container_width=True, key="insights_cluster_scatter")
    else:
        ui_components.empty_state("Click 'Train Models' to discover your day patterns.", icon="")

