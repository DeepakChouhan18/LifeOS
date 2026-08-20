"""
Streamlit UI for the unified LifeOS Dashboard.

Design philosophy:
  - Answers "What matters to me today?" — not "here are all my database records"
  - Greeting + date → Today summary cards → Priorities → Insights → Consistency Score
  - Progressive disclosure: deep analytics are in individual module pages
"""

import streamlit as st
from datetime import date

from database import cache
from utils import ui_components, date_helpers, auth as auth_utils


def render(user_id: int):
    # Dashboard is read-only — no DB session needed; all data comes from cache.
    user_name = cache.get_user_display_name(user_id) or auth_utils.get_current_display_name()

    greet_text, today_str = date_helpers.greeting(), date_helpers.today_label()

    # ---- Hero greeting ----
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:2rem; padding-bottom:1.5rem; border-bottom:1px solid rgba(255,255,255,0.07);">
            <div>
                <div style="font-size:1.9rem; font-weight:800; color:#ffffff; letter-spacing:-0.035em; margin-bottom:0.3rem; line-height:1.2;">
                    {greet_text}, <span style="background:linear-gradient(135deg, #a5b4fc 0%, #818cf8 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">{user_name}</span>.
                </div>
                <div style="font-size:0.88rem; color:#64748b; font-weight:400;">
                    Here is your personal analytics and consistency overview for today.
                </div>
            </div>
            <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:999px; padding:0.35rem 0.9rem; font-size:0.78rem; font-weight:600; color:#94a3b8; letter-spacing:0.02em;">
                {today_str}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    summary = cache.get_dashboard_combined_summary(user_id)

    # ---- TODAY summary cards ----
    _render_today_cards(summary)

    st.markdown("<div style='height:1.25rem;'></div>", unsafe_allow_html=True)

    # ---- Two-column: Priorities | Insights ----
    col_left, col_right = st.columns([1, 1], gap="large")
    with col_left:
        _render_priorities(summary)
    with col_right:
        _render_insights(summary)

    st.markdown("<hr style='border-color:#1a2540; margin:1.75rem 0;'>", unsafe_allow_html=True)

    # ---- Consistency Score ----
    _render_consistency_score(summary)


# ---------------------------------------------------------------------------
# Sub-sections
# ---------------------------------------------------------------------------

def _render_today_cards(summary):
    ui_components.section_header("TODAY", icon="")

    study = summary["study"]
    health = summary["health"]
    finance = summary["finance"]

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        today_h = study.get("today_hours", 0)
        goal_h = study.get("daily_goal_hours", 5)
        pct = study.get("today_goal_pct", 0)
        delta = f"{pct:.0f}% of daily goal"
        ui_components.metric_card(
            label="Study",
            value=f"{today_h:.1f} h",
            subtitle=f"Goal {goal_h:.0f} h",
            delta=delta,
            delta_type="up" if pct >= 80 else ("neutral" if pct >= 30 else "down"),
            accent_color="#6366f1",
        )

    with c2:
        cal_today = health.get("calories_today", 0)
        cal_target = health.get("calorie_target", 2200)
        weight = health.get("latest_weight")
        weight_str = f"{weight:.1f} kg" if weight else "—"
        cal_pct = (cal_today / cal_target * 100) if cal_target else 0
        ui_components.metric_card(
            label="Calories",
            value=f"{cal_today:.0f} kcal",
            subtitle=f"Target {cal_target:.0f} · Weight {weight_str}",
            delta=f"{cal_pct:.0f}% of target",
            delta_type="neutral" if 80 <= cal_pct <= 110 else ("up" if cal_pct <= 100 else "down"),
            accent_color="#10b981",
        )

    with c3:
        spent = finance.get("today_spent", 0)
        daily_rem = finance.get("daily_budget_remaining", 0)
        ui_components.metric_card(
            label="Spent Today",
            value=f"₹{spent:.0f}",
            subtitle=f"₹{daily_rem:.0f} daily budget left",
            accent_color="#f59e0b",
        )

    with c4:
        streak = study.get("current_streak", 0)
        longest = study.get("longest_streak", 0)
        ui_components.metric_card(
            label="Study Streak",
            value=f"{streak} days",
            subtitle=f"Longest {longest} days",
            delta="7-day streak active" if streak >= 7 else "",
            delta_type="up" if streak >= 7 else "neutral",
            accent_color="#a855f7",
        )


def _render_priorities(summary):
    ui_components.section_header("TODAY'S FOCUS")
    priorities = summary.get("priorities", [])

    if not priorities:
        ui_components.empty_state(
            "No priorities yet",
            icon="",
            hint="Add high-priority tasks in Study to populate this list.",
        )
        return

    for p in priorities:
        done = p.get("done", False)
        label = p.get("label", "")
        task_class = "los-task-label los-task-done" if done else "los-task-label"
        icon = "✓" if done else "○"
        icon_color = "#22c55e" if done else "#475569"
        st.markdown(
            f'<div class="los-task-row">'
            f'<span style="color:{icon_color}; font-size:0.9rem; flex-shrink:0;">{icon}</span>'
            f'<span class="{task_class}">{label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.25rem;'></div>", unsafe_allow_html=True)

    # Quick action buttons
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("+ Add Task", key="dash_add_task", use_container_width=True):
            st.session_state.page = "Study"
            st.rerun()
    with col_b:
        if st.button("Study Session", key="dash_study", use_container_width=True):
            st.session_state.page = "Study"
            st.rerun()


def _render_insights(summary):
    ui_components.section_header("INSIGHTS")
    insights = summary.get("insights", [])

    if not insights:
        ui_components.empty_state(
            "No insights yet",
            icon="",
            hint="Keep logging data for a few days to unlock personalized insights.",
        )
        return

    for insight in insights:
        ui_components.insight_card(insight)


def _render_consistency_score(summary):
    ui_components.section_header(
        "PERSONAL CONSISTENCY SCORE",
        subtitle="A weighted average you control — not an objective life score. Adjust weights in Settings.",
    )

    scores = summary["scores"]
    weights = summary["weights"]

    ui_components.consistency_score_display(
        overall=scores["overall"],
        study=scores["study"],
        health=scores["health"],
        finance=scores["finance"],
        study_w=weights["study"],
        health_w=weights["health"],
        finance_w=weights["finance"],
    )
