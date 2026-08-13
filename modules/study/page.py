"""
Streamlit UI for the Study module.

Features:
- Independent section display
- Today overview & fast actions
- Task management (priority, topic, due date, edit, complete/uncomplete, delete)
- Subject management
- Session logging & session history with edit/delete
- Interactive Plotly analytics (subject breakdown, rolling trend, streak summary)
"""

import streamlit as st
from datetime import date, datetime, timezone

from database.connection import get_session
from modules.study import crud, analytics
from utils.charts import subject_minutes_bar, rolling_weekly_line
from utils import ui_components, date_helpers
from config import DEFAULT_USER_ID


def render():
    ui_components.page_header("📚 Study Module", "Track tasks, study sessions, streak consistency, and subject breakdowns.")

    db = get_session()
    try:
        tab_today, tab_tasks, tab_sessions, tab_subjects, tab_analytics = st.tabs([
            "📅 Today", "📝 Tasks", "⏱️ Study Sessions", "📖 Subjects", "📈 Analytics"
        ])

        with tab_today:
            _render_today_tab(db)

        with tab_tasks:
            _render_tasks_tab(db)

        with tab_sessions:
            _render_sessions_tab(db)

        with tab_subjects:
            _render_subjects_tab(db)

        with tab_analytics:
            _render_analytics_tab(db)

    finally:
        db.close()


def _render_today_tab(db):
    summary = analytics.get_today_summary(db, DEFAULT_USER_ID)
    streaks = analytics.get_streak_summary(db, DEFAULT_USER_ID)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Today's Study", f"{summary['today_hours']} h", f"Goal: {summary['daily_goal_hours']} h")
    c2.metric("Goal Progress", f"{summary['goal_pct']}%")
    c3.metric("Current Streak", f"{streaks['current_streak']} days", f"Longest: {streaks['longest_streak']} d")
    c4.metric("Tasks Completed Today", f"{summary['completed_tasks']}")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚡ Quick Log Study Session")
        subjects = crud.list_subjects(db, DEFAULT_USER_ID)
        subject_names = [s.name for s in subjects]

        if not subject_names:
            st.warning("Please add at least one Subject in the Subjects tab first.")
        else:
            with st.form("quick_log_session_form", clear_on_submit=True):
                subj_name = st.selectbox("Subject", subject_names)
                minutes = st.number_input("Duration (minutes)", min_value=5, max_value=600, value=45, step=5)
                topic = st.text_input("Topic / Notes (optional)")
                submitted = st.form_submit_button("Log Session")

                if submitted:
                    subj = next((s for s in subjects if s.name == subj_name), None)
                    crud.log_session(db, DEFAULT_USER_ID, subj.id, int(minutes), date.today(), topic=topic)
                    st.success(f"Logged {minutes} min of {subj_name}!")
                    st.rerun()

        st.divider()
        _render_study_timer(db, subjects)

    with col2:
        st.subheader("📋 Pending Tasks")
        pending_tasks = [t for t in crud.list_tasks(db, DEFAULT_USER_ID, include_completed=False)]
        if not pending_tasks:
            ui_components.empty_state("No pending tasks! Great job.", "🎉")
        else:
            for task in pending_tasks[:5]:
                t_col1, t_col2 = st.columns([4, 1])
                badge = "🔴" if task.priority == "high" else ("🟡" if task.priority == "medium" else "🟢")
                t_col1.write(f"{badge} **{task.title}** ({task.subject.name if task.subject else 'General'})")
                if t_col2.button("Done", key=f"quick_complete_{task.id}"):
                    crud.complete_task(db, task.id)
                    st.rerun()


def _render_study_timer(db, subjects):
    """
    A simple start/finish study timer. Elapsed time is computed from a
    stored start timestamp (session_state), so it stays accurate across
    Streamlit reruns without needing a background thread. On "Finish",
    the elapsed minutes are automatically saved as a study session —
    no manual duration entry needed.
    """
    st.subheader("▶️ Study Timer")
    subject_names = [s.name for s in subjects]

    if "timer_start" not in st.session_state:
        st.session_state.timer_start = None
        st.session_state.timer_subject = None

    if st.session_state.timer_start is None:
        if not subject_names:
            st.caption("Add a subject first to use the timer.")
            return
        timer_subject = st.selectbox("Subject", subject_names, key="timer_subject_select")
        if st.button("▶ Start Timer", type="primary"):
            st.session_state.timer_start = datetime.now(timezone.utc)
            st.session_state.timer_subject = timer_subject
            st.rerun()
    else:
        elapsed = datetime.now(timezone.utc) - st.session_state.timer_start
        elapsed_minutes = int(elapsed.total_seconds() // 60)
        elapsed_seconds = int(elapsed.total_seconds() % 60)
        st.metric(f"Studying: {st.session_state.timer_subject}", f"{elapsed_minutes:02d}:{elapsed_seconds:02d}")
        st.caption("Timer runs in the background — refresh or interact with the page to update the display.")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 Refresh"):
                st.rerun()
        with col_b:
            if st.button("⏹ Finish & Save", type="primary"):
                subj = next((s for s in subjects if s.name == st.session_state.timer_subject), None)
                duration = max(1, elapsed_minutes)
                if subj:
                    crud.log_session(db, DEFAULT_USER_ID, subj.id, duration, date.today(),
                                      topic="Timed session")
                    st.success(f"Saved {duration} min session for {subj.name}")
                st.session_state.timer_start = None
                st.session_state.timer_subject = None
                st.rerun()


def _render_tasks_tab(db):
    st.subheader("Task Management")

    col_add, col_list = st.columns([1, 2])

    with col_add:
        st.markdown("##### Add New Task")
        subjects = crud.list_subjects(db, DEFAULT_USER_ID)
        subject_names = [s.name for s in subjects]

        with st.form("add_task_form", clear_on_submit=True):
            title = st.text_input("Task Title")
            subject_name = st.selectbox("Subject", subject_names) if subject_names else None
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=1)
            topic = st.text_input("Topic (optional)")
            due = st.date_input("Due Date", value=date.today())
            submitted = st.form_submit_button("Add Task")

            if submitted and title:
                subject = next((s for s in subjects if s.name == subject_name), None) if subject_name else None
                crud.add_task(db, DEFAULT_USER_ID, title, subject.id if subject else None, due, priority, topic)
                st.success(f"Added: {title}")
                st.rerun()

    with col_list:
        st.markdown("##### All Tasks")
        tasks = crud.list_tasks(db, DEFAULT_USER_ID, include_completed=True)
        if not tasks:
            ui_components.empty_state("No tasks created yet.")
            return

        for task in tasks:
            with st.expander(f"{'✅' if task.is_completed else '🔲'} {task.title} ({task.subject.name if task.subject else 'General'})", expanded=not task.is_completed):
                st.write(f"**Priority:** {task.priority.upper()} | **Due:** {task.due_date or 'No deadline'} | **Topic:** {task.topic or 'N/A'}")
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if task.is_completed:
                        if st.button("Mark Pending", key=f"uncomp_{task.id}"):
                            crud.uncomplete_task(db, task.id)
                            st.rerun()
                    else:
                        if st.button("Mark Complete", key=f"comp_{task.id}"):
                            crud.complete_task(db, task.id)
                            st.rerun()
                with col_btn2:
                    if st.button("Delete Task", key=f"del_task_{task.id}"):
                        crud.delete_task(db, task.id)
                        st.rerun()


def _render_sessions_tab(db):
    st.subheader("Study Sessions Log")

    col_log, col_hist = st.columns([1, 2])

    with col_log:
        st.markdown("##### Log Session")
        subjects = crud.list_subjects(db, DEFAULT_USER_ID)
        subject_names = [s.name for s in subjects]

        with st.form("log_session_full_form", clear_on_submit=True):
            subject_name = st.selectbox("Subject", subject_names) if subject_names else None
            minutes = st.number_input("Duration (minutes)", min_value=5, max_value=600, value=45, step=5)
            session_date = st.date_input("Date", value=date.today())
            topic = st.text_input("Topic")
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save Session")

            if submitted and subject_name:
                subject = next((s for s in subjects if s.name == subject_name), None)
                crud.log_session(db, DEFAULT_USER_ID, subject.id, int(minutes), session_date, topic, notes)
                st.success("Session logged")
                st.rerun()

    with col_hist:
        st.markdown("##### Session History")
        sessions = crud.list_sessions(db, DEFAULT_USER_ID, limit=50)
        if not sessions:
            ui_components.empty_state("No study sessions logged yet.")
            return

        for s in sessions:
            c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
            c1.write(f"**{s.session_date}**")
            c2.write(f"**{s.subject.name if s.subject else 'General'}**: {s.duration_minutes} min")
            c3.caption(s.topic or s.notes or "")
            if c4.button("🗑️", key=f"del_sess_{s.id}"):
                crud.delete_session(db, s.id)
                st.rerun()


def _render_subjects_tab(db):
    st.subheader("Manage Subjects")

    col_add, col_list = st.columns([1, 2])
    with col_add:
        with st.form("add_subject_form", clear_on_submit=True):
            name = st.text_input("Subject Name (e.g. DSA, SQL, ML)")
            color = st.color_picker("Subject Color", value="#6366f1")
            submitted = st.form_submit_button("Add Subject")

            if submitted and name:
                crud.add_subject(db, DEFAULT_USER_ID, name, color)
                st.success(f"Added subject: {name}")
                st.rerun()

    with col_list:
        subjects = crud.list_subjects(db, DEFAULT_USER_ID)
        if not subjects:
            ui_components.empty_state("No subjects added yet.")
            return
        for s in subjects:
            sc1, sc2 = st.columns([4, 1])
            sc1.markdown(f"<span style='color:{s.color}; font-weight:bold;'>■</span> **{s.name}**", unsafe_allow_html=True)
            if sc2.button("Delete", key=f"del_subj_{s.id}"):
                crud.delete_subject(db, s.id)
                st.rerun()


def _render_analytics_tab(db):
    st.subheader("Study Analytics")
    summary = analytics.get_full_summary(db, DEFAULT_USER_ID)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Streak", f"{summary['current_streak']} days")
    c2.metric("Longest Streak", f"{summary['longest_streak']} days")
    c3.metric("Task Completion Rate", f"{summary['completion_pct']}%")
    c4.metric("Total Study Hours", f"{summary['total_study_hours']} h")

    st.divider()

    subject_df = analytics.get_subject_breakdown_df(db, DEFAULT_USER_ID)
    weekly_df = analytics.get_weekly_trend_df(db, DEFAULT_USER_ID)

    col1, col2 = st.columns(2)
    with col1:
        fig = subject_minutes_bar(subject_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="study_subject_bar")
        else:
            ui_components.empty_state("No subject breakdown data yet.")
    with col2:
        fig = rolling_weekly_line(weekly_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="study_rolling_line")
        else:
            ui_components.empty_state("Not enough data for rolling weekly trend.")
