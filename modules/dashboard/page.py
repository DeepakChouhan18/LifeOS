"""
Streamlit UI for the unified LifeOS Overview Dashboard.

Combines high-level daily summaries across Study, Health, and Finance:
- Personalized greeting with user's name
- Today's high-level summary cards (Study, Health, Finance, Streak)
- Smart, data-driven insights powered by raw SQL analytics
- Overall Productivity Score & per-module score breakdown
"""

import streamlit as st
import plotly.express as px
import pandas as pd

from database.connection import get_session
from modules.dashboard import aggregator
from modules.settings import crud as settings_crud
from utils import ui_components, date_helpers
from config import DEFAULT_USER_ID


def render():
    db = get_session()
    try:
        profile = settings_crud.get_user_profile(db, DEFAULT_USER_ID)
        user_name = profile.name if profile else "Friend"

        greet_text = date_helpers.greeting()
        ui_components.page_header(f"{greet_text}, {user_name} 👋", "Here is your personal daily life summary across Study, Health, and Finance.")

        summary = aggregator.get_combined_summary(db, DEFAULT_USER_ID)

        _render_today_overview(summary)

        st.divider()

        _render_priorities(summary)

        st.divider()

        _render_smart_insights(summary)

        st.divider()

        _render_consistency_score(summary)

    finally:
        db.close()


def _render_priorities(summary):
    st.subheader("Today's Priorities")
    priorities = summary.get("priorities", [])
    if not priorities:
        ui_components.empty_state("No priorities yet — add tasks or log today's health data.")
        return
    for p in priorities:
        st.checkbox(p["label"], value=p["done"], disabled=True, key=f"priority_{p['label']}")


def _render_today_overview(summary):
    st.subheader("Today at a Glance")

    study_sum = summary["study"]
    health_sum = summary["health"]
    finance_sum = summary["finance"]

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown("**📚 STUDY**")
        hours_str = f"{study_sum.get('today_hours', 0):.1f} / {study_sum.get('daily_goal_hours', 5):.1f} hours"
        pct_str = f"{study_sum.get('today_goal_pct', 0):.0f}% complete"
        st.metric("Study Today", hours_str, pct_str)

    with c2:
        st.markdown("**💪 HEALTH**")
        cal_str = f"{health_sum.get('calories_today', 0):.0f} / {health_sum.get('calorie_target', 2200):.0f} kcal"
        prot_str = f"{health_sum.get('protein_today', 0):.0f} / {health_sum.get('protein_target_g', 130):.0f} g protein"
        st.metric("Calories Today", cal_str, prot_str)

    with c3:
        st.markdown("**💰 FINANCE**")
        spend_str = f"₹{finance_sum.get('today_spent', 0):.0f} spent today"
        rem_str = f"₹{finance_sum.get('daily_budget_remaining', 0):.0f} daily budget left"
        st.metric("Expenses Today", spend_str, rem_str)

    with c4:
        st.markdown("**🔥 STREAK**")
        streak_str = f"{study_sum.get('current_streak', 0)} days"
        long_str = f"Longest: {study_sum.get('longest_streak', 0)} days"
        st.metric("Current Streak", streak_str, long_str)


def _render_smart_insights(summary):
    st.subheader("💡 Smart Data Insights")
    insights = summary.get("insights", [])

    if not insights:
        ui_components.empty_state("Keep logging data to unlock automated insights.")
        return

    for insight in insights:
        ui_components.insight_card(insight)


def _render_consistency_score(summary):
    st.subheader("📈 Personal Consistency Score")

    scores = summary["scores"]
    weights = summary["weights"]

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric("Consistency Score", f"{scores['overall']:.1f} / 100")
        st.caption(
            f"A simple weighted average YOU control — not an objective measure "
            f"of your life. Current weights: Study {weights['study']*100:.0f}% · "
            f"Health {weights['health']*100:.0f}% · Finance {weights['finance']*100:.0f}%. "
            "Adjust these in Settings."
        )

    with col2:
        df = pd.DataFrame({
            "Module": ["Study", "Health", "Finance"],
            "Score": [scores["study"], scores["health"], scores["finance"]],
        })
        fig = px.bar(
            df, x="Module", y="Score", range_y=[0, 100], color="Module",
            title="Module Scores (0-100)",
            color_discrete_sequence=["#38BDF8", "#818CF8", "#10B981"]
        )
        fig.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", showlegend=False, height=250
        )
        st.plotly_chart(fig, use_container_width=True, key="dash_module_scores_bar")
