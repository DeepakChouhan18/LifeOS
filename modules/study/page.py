"""
Streamlit UI for the Study module.

Features:
- Today overview with metric cards and focus timer
- Task management (priority, topic, due date, complete/uncomplete, delete)
- Subject management
- Session logging & history with delete
- Interactive Plotly analytics (subject breakdown, rolling trend, streak summary)
- Study timer (stores in session_state, saves on finish)
"""

import time
import streamlit as st
from datetime import date, datetime, timezone

from database.connection import get_session
from modules.study import crud, analytics
from utils.charts import subject_minutes_bar, rolling_weekly_line
from utils import ui_components, date_helpers


def render(user_id: int):
    ui_components.page_header(
        "Study",
        "Track sessions, manage tasks, monitor streaks, and analyze your progress.",
    )

    db = get_session()
    try:
        tab_today, tab_tasks, tab_sessions, tab_subjects, tab_analytics = st.tabs([
            "Today", "Tasks", "Sessions", "Subjects", "Analytics"
        ])

        with tab_today:
            _render_today_tab(db, user_id)

        with tab_tasks:
            _render_tasks_tab(db, user_id)

        with tab_sessions:
            _render_sessions_tab(db, user_id)

        with tab_subjects:
            _render_subjects_tab(db, user_id)

        with tab_analytics:
            _render_analytics_tab(db, user_id)

    finally:
        db.close()


# ==========================================================================
# TODAY TAB
# ==========================================================================

def _render_today_tab(db, user_id: int):
    summary = analytics.get_today_summary(db, user_id)
    streaks = analytics.get_streak_summary(db, user_id)

    # ---- Metric cards ----
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui_components.metric_card(
            "Today's Study",
            f"{summary['today_hours']} h",
            subtitle=f"Goal {summary['daily_goal_hours']} h",
            accent_color="#6366f1",
        )
    with c2:
        pct = summary['goal_pct']
        ui_components.metric_card(
            "Goal Progress",
            f"{pct}%",
            subtitle="of today's target",
            delta="On track" if pct >= 50 else "Behind",
            delta_type="up" if pct >= 50 else "down",
            accent_color="#6366f1",
        )
    with c3:
        ui_components.metric_card(
            "Study Streak",
            f"{streaks['current_streak']} days",
            subtitle=f"Longest {streaks['longest_streak']} d",
            accent_color="#6366f1",
        )
    with c4:
        ui_components.metric_card(
            "Tasks Done",
            f"{summary['completed_tasks']}",
            subtitle="today",
            accent_color="#6366f1",
        )

    # Progress bar
    if summary['daily_goal_hours'] > 0:
        progress_val = min(1.0, summary['today_hours'] / summary['daily_goal_hours'])
        st.progress(progress_val)
        st.caption(f"{summary['today_hours']:.1f} h of {summary['daily_goal_hours']:.0f} h daily goal")

    st.markdown("<hr style='border-color:#1a2540;margin:1.25rem 0;'>", unsafe_allow_html=True)

    # ---- Study timer (prominent) ----
    subjects = crud.list_subjects(db, user_id)
    _render_study_timer(db, subjects, user_id)

    st.markdown("<hr style='border-color:#1a2540;margin:1.25rem 0;'>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        ui_components.section_header("QUICK LOG SESSION")
        subject_names = [s.name for s in subjects]

        if not subject_names:
            ui_components.info_banner(
                "Add at least one Subject in the Subjects tab before logging sessions.",
                banner_type="warning",
            )
        else:
            with st.form("quick_log_session_form", clear_on_submit=True):
                subj_name = st.selectbox("Subject", subject_names)
                minutes = st.number_input("Duration (minutes)", min_value=5, max_value=600, value=45, step=5)
                topic = st.text_input("Topic / Notes (optional)")
                submitted = st.form_submit_button("+ Log Session", type="primary", use_container_width=True)

                if submitted:
                    subj = next((s for s in subjects if s.name == subj_name), None)
                    crud.log_session(db, user_id, subj.id, int(minutes), date.today(), topic=topic)
                    st.success(f"Logged {minutes} min of {subj_name}.")
                    st.rerun()

    with col2:
        ui_components.section_header("PENDING TASKS")
        pending_tasks = [t for t in crud.list_tasks(db, user_id, include_completed=False)]
        if not pending_tasks:
            ui_components.empty_state(
                "All clear — no pending tasks",
                icon="",
                hint="Add tasks in the Tasks tab to track your study goals.",
            )
        else:
            for task in pending_tasks[:6]:
                today_d = date.today()
                is_overdue = task.due_date and task.due_date < today_d

                if task.priority == "high":
                    accent = "#ef4444"
                elif task.priority == "medium":
                    accent = "#f59e0b"
                else:
                    accent = "#22c55e"

                t_col1, t_col2 = st.columns([5, 1])
                with t_col1:
                    subj_name_str = task.subject.name if task.subject else "General"
                    overdue_badge = ui_components.status_badge("Overdue", "overdue") if is_overdue else ""
                    st.markdown(
                        f'<div style="padding:0.55rem 0.75rem;background:#111927;border-radius:8px;'
                        f'margin-bottom:0.35rem;border:1px solid #1e293b;border-left:2px solid {accent};">'
                        f'<div style="font-size:0.875rem;font-weight:500;color:#e2e8f0;">{task.title}</div>'
                        f'<div style="font-size:0.75rem;color:#64748b;margin-top:0.1rem;">'
                        f'{subj_name_str} {overdue_badge}</div></div>',
                        unsafe_allow_html=True,
                    )
                with t_col2:
                    if st.button("Done", key=f"quick_complete_{task.id}", use_container_width=True):
                        crud.complete_task(db, task.id)
                        st.rerun()


# ==========================================================================
# STUDY TIMER
# ==========================================================================

@st.fragment(run_every="1s")
def _render_study_timer(db, subjects, user_id: int):
    """
    Isolated timer fragment. Automatically reruns every 1 second via
    Streamlit native fragment scheduling when a timer is running.
    """
    subject_names = [s.name for s in subjects]

    if "timer_start" not in st.session_state:
        st.session_state.timer_start = None
        st.session_state.timer_subject = None

    if st.session_state.timer_start is None:
        ui_components.section_header("STUDY TIMER")
        if not subject_names:
            st.caption("Add a subject first to use the timer.")
            return

        col_sel, col_start = st.columns([3, 1])
        with col_sel:
            timer_subject = st.selectbox("Select subject", subject_names, key="timer_subject_select")
        with col_start:
            st.markdown("<div style='margin-top:1.55rem;'></div>", unsafe_allow_html=True)
            if st.button("Start Timer", type="primary", use_container_width=True, key="timer_start_btn"):
                st.session_state.timer_start = datetime.now(timezone.utc)
                st.session_state.timer_subject = timer_subject
                st.rerun()
    else:
        now = datetime.now(timezone.utc)
        elapsed_sec = int((now - st.session_state.timer_start).total_seconds())
        elapsed_minutes = elapsed_sec // 60
        elapsed_seconds = elapsed_sec % 60

        ui_components.section_header("TIMER RUNNING")

        col_timer, col_controls = st.columns([2, 1], gap="large")
        with col_timer:
            ui_components.timer_display(elapsed_minutes, elapsed_seconds, st.session_state.timer_subject)

        with col_controls:
            st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
            if st.button("Finish & Save", type="primary", use_container_width=True, key="timer_finish"):
                subj = next((s for s in subjects if s.name == st.session_state.timer_subject), None)
                duration = max(1, round(elapsed_sec / 60.0))
                if subj:
                    crud.log_session(db, user_id, subj.id, duration, date.today(), topic="Timed session")
                    st.success(f"Saved {duration} min session for {subj.name}.")
                st.session_state.timer_start = None
                st.session_state.timer_subject = None
                st.rerun()
            st.markdown("<div style='margin-top:0.4rem;'></div>", unsafe_allow_html=True)
            if st.button("Cancel", use_container_width=True, key="timer_cancel"):
                st.session_state.timer_start = None
                st.session_state.timer_subject = None
                st.rerun()


# ==========================================================================
# TASKS TAB
# ==========================================================================

def _render_tasks_tab(db, user_id: int):
    col_add, col_list = st.columns([1, 2], gap="large")

    with col_add:
        ui_components.section_header("ADD TASK")
        subjects = crud.list_subjects(db, user_id)
        subject_names = [s.name for s in subjects]

        with st.form("add_task_form", clear_on_submit=True):
            title = st.text_input("Task Title", placeholder="e.g. Complete DSA Chapter 5")
            subject_name = st.selectbox("Subject", subject_names) if subject_names else None
            priority = st.selectbox(
                "Priority", ["low", "medium", "high"], index=1,
                format_func=lambda x: {"low": "Low", "medium": "Medium", "high": "High"}[x],
            )
            topic = st.text_input("Topic (optional)")
            due = st.date_input("Due Date", value=date.today())
            submitted = st.form_submit_button("+ Add Task", type="primary", use_container_width=True)

            if submitted and title:
                subject = next((s for s in subjects if s.name == subject_name), None) if subject_name else None
                crud.add_task(db, user_id, title, subject.id if subject else None, due, priority, topic)
                st.success(f"Added: {title}")
                st.rerun()
            elif submitted and not title:
                st.error("Please enter a task title.")

    with col_list:
        tasks = crud.list_tasks(db, user_id, include_completed=True)
        if not tasks:
            ui_components.empty_state(
                "No tasks yet",
                icon="",
                hint="Use the form to add your first study task.",
            )
            return

        pending = [t for t in tasks if not t.is_completed]
        completed = [t for t in tasks if t.is_completed]

        if pending:
            ui_components.section_header(f"PENDING ({len(pending)})")
            for task in pending:
                _render_task_row(db, task)

        if completed:
            ui_components.section_header(f"COMPLETED ({len(completed)})")
            for task in completed:
                _render_task_row(db, task)


def _render_task_row(db, task):
    today_d = date.today()
    is_overdue = (not task.is_completed) and task.due_date and task.due_date < today_d

    if task.priority == "high":
        accent = "#ef4444"
        prio_label = "High"
        prio_variant = "danger"
    elif task.priority == "medium":
        accent = "#f59e0b"
        prio_label = "Medium"
        prio_variant = "warning"
    else:
        accent = "#22c55e"
        prio_label = "Low"
        prio_variant = "success"

    icon = "✓" if task.is_completed else ("!" if is_overdue else "○")
    icon_color = "#22c55e" if task.is_completed else ("#ef4444" if is_overdue else "#475569")
    subj_str = task.subject.name if task.subject else "General"
    due_str = f"Due {date_helpers.format_date(task.due_date)}" if task.due_date else ""
    text_color = "#64748b" if task.is_completed else "#e2e8f0"
    text_style = "text-decoration:line-through;" if task.is_completed else ""

    with st.expander(f"{task.title}", expanded=False):
        st.markdown(
            f'<div style="font-size:0.78rem;color:#64748b;margin-bottom:0.5rem;">'
            f'{subj_str}'
            + (f' · {due_str}' if due_str else '')
            + f' · {ui_components.status_badge(prio_label, prio_variant)}'
            + (f' {ui_components.status_badge("Overdue", "overdue")}' if is_overdue else '')
            + (f'<br>Topic: {task.topic}' if task.topic else '')
            + '</div>',
            unsafe_allow_html=True,
        )
        col_btn1, col_btn2, _ = st.columns([1, 1, 3])
        with col_btn1:
            if task.is_completed:
                if st.button("Undo", key=f"uncomp_{task.id}", use_container_width=True):
                    crud.uncomplete_task(db, task.id)
                    st.rerun()
            else:
                if st.button("Complete", key=f"comp_{task.id}", type="primary", use_container_width=True):
                    crud.complete_task(db, task.id)
                    st.rerun()
        with col_btn2:
            if st.button("Delete", key=f"del_task_{task.id}", use_container_width=True):
                crud.delete_task(db, task.id)
                st.rerun()


# ==========================================================================
# SESSIONS TAB
# ==========================================================================

def _render_sessions_tab(db, user_id: int):
    col_log, col_hist = st.columns([1, 2], gap="large")

    with col_log:
        ui_components.section_header("LOG SESSION")
        subjects = crud.list_subjects(db, user_id)
        subject_names = [s.name for s in subjects]

        with st.form("log_session_full_form", clear_on_submit=True):
            subject_name = st.selectbox("Subject", subject_names) if subject_names else None
            minutes = st.number_input("Duration (minutes)", min_value=5, max_value=600, value=45, step=5)
            session_date = st.date_input("Date", value=date.today())
            topic = st.text_input("Topic")
            notes = st.text_area("Notes", height=80)
            submitted = st.form_submit_button("Save Session", type="primary", use_container_width=True)

            if submitted and subject_name:
                subject = next((s for s in subjects if s.name == subject_name), None)
                crud.log_session(db, user_id, subject.id, int(minutes), session_date, topic, notes)
                st.success("Session logged.")
                st.rerun()
            elif submitted and not subject_name:
                ui_components.info_banner("Add a subject first.", banner_type="warning")

    with col_hist:
        ui_components.section_header("HISTORY")
        sessions = crud.list_sessions(db, user_id, limit=50)
        if not sessions:
            ui_components.empty_state(
                "No study sessions yet",
                icon="",
                hint="Start your first session using the Quick Log or Timer.",
            )
            return

        for s in sessions:
            date_label = date_helpers.format_date(s.session_date)
            subj_name = s.subject.name if s.subject else "General"
            note_str = s.topic or s.notes or ""

            col_d, col_s, col_n, col_del = st.columns([1.5, 2, 2, 0.5])
            col_d.markdown(f'<span style="font-size:0.8rem;color:#64748b;">{date_label}</span>', unsafe_allow_html=True)
            col_s.markdown(
                f'<span style="font-weight:600;font-size:0.875rem;color:#e2e8f0;">{subj_name}</span> '
                f'<span style="font-size:0.8rem;color:#64748b;">{s.duration_minutes} min</span>',
                unsafe_allow_html=True,
            )
            col_n.markdown(f'<span style="font-size:0.78rem;color:#64748b;">{note_str}</span>', unsafe_allow_html=True)
            if col_del.button("✕", key=f"del_sess_{s.id}"):
                crud.delete_session(db, s.id)
                st.rerun()
            st.markdown('<hr style="border-color:#1a2540;margin:0.25rem 0;">', unsafe_allow_html=True)


# ==========================================================================
# SUBJECTS TAB
# ==========================================================================

def _render_subjects_tab(db, user_id: int):
    col_add, col_list = st.columns([1, 2], gap="large")

    with col_add:
        ui_components.section_header("ADD SUBJECT")
        with st.form("add_subject_form", clear_on_submit=True):
            name = st.text_input("Subject Name", placeholder="e.g. DSA, SQL, Machine Learning")
            color = st.color_picker("Color", value="#6366f1")
            submitted = st.form_submit_button("+ Add Subject", type="primary", use_container_width=True)

            if submitted and name:
                crud.add_subject(db, user_id, name, color)
                st.success(f"Added: {name}")
                st.rerun()
            elif submitted:
                st.error("Please enter a subject name.")

    with col_list:
        ui_components.section_header("YOUR SUBJECTS")
        subjects = crud.list_subjects(db, user_id)
        if not subjects:
            ui_components.empty_state(
                "No subjects yet",
                icon="",
                hint="Add subjects like DSA, Python, or SQL to organize your sessions.",
            )
            return
        for s in subjects:
            sc1, sc2 = st.columns([5, 1])
            sc1.markdown(
                f'<div style="padding:0.6rem 0.9rem;background:#111927;border-radius:8px;'
                f'margin-bottom:0.35rem;border:1px solid #1e293b;border-left:3px solid {s.color};">'
                f'<span style="font-weight:600;color:#e2e8f0;">{s.name}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if sc2.button("✕", key=f"del_subj_{s.id}", use_container_width=True):
                crud.delete_subject(db, s.id)
                st.rerun()


# ==========================================================================
# ANALYTICS TAB
# ==========================================================================

def _render_analytics_tab(db, user_id: int):
    summary = analytics.get_full_summary(db, user_id)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui_components.metric_card("Current Streak", f"{summary['current_streak']} days", accent_color="#6366f1")
    with c2:
        ui_components.metric_card("Longest Streak", f"{summary['longest_streak']} days", accent_color="#6366f1")
    with c3:
        ui_components.metric_card("Task Completion", f"{summary['completion_pct']}%", accent_color="#6366f1")
    with c4:
        ui_components.metric_card("Total Hours", f"{summary['total_study_hours']} h", accent_color="#6366f1")

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

    subject_df = analytics.get_subject_breakdown_df(db, user_id)
    weekly_df = analytics.get_weekly_trend_df(db, user_id)

    col1, col2 = st.columns(2)
    with col1:
        fig = subject_minutes_bar(subject_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="study_subject_bar")
        else:
            ui_components.empty_state(
                "No subject data yet",
                icon="",
                hint="Log sessions with different subjects to see the breakdown.",
            )
    with col2:
        fig = rolling_weekly_line(weekly_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="study_rolling_line")
        else:
            ui_components.empty_state(
                "Not enough data for trend analysis",
                icon="",
                hint="Log at least a week of sessions to see your rolling trend.",
            )
