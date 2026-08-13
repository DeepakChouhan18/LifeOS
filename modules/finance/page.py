"""
Streamlit UI for the Finance module.

Features:
- Independent module navigation
- Today's spending & daily remaining budget tracking
- Fast expense logging with payment method support (UPI, Cash, Card)
- Category budgets with limit alerts
- Expense history with edit and delete capabilities
- Interactive Plotly analytics (category spend, budget remaining, rolling spend line)
"""

import streamlit as st
from datetime import date

from database.connection import get_session
from modules.finance import crud, analytics
from utils.charts import category_spend_pie, budget_remaining_bar, spend_trend_line
from utils import ui_components, date_helpers
from config import DEFAULT_USER_ID, DEFAULT_EXPENSE_CATEGORIES


def render():
    ui_components.page_header("💰 Finance Module", "Track daily expenses, manage monthly category budgets, and analyze spending patterns.")

    db = get_session()
    try:
        _ensure_default_categories(db)

        tab_overview, tab_expenses, tab_budget, tab_analytics = st.tabs([
            "📊 Overview", "💸 Expenses", "🎯 Budgets", "📈 Analytics"
        ])

        with tab_overview:
            _render_overview_tab(db)

        with tab_expenses:
            _render_expenses_tab(db)

        with tab_budget:
            _render_budget_tab(db)

        with tab_analytics:
            _render_analytics_tab(db)

    finally:
        db.close()


def _ensure_default_categories(db):
    for name in DEFAULT_EXPENSE_CATEGORIES:
        crud.get_or_create_category(db, DEFAULT_USER_ID, name)


def _render_overview_tab(db):
    summary = analytics.get_current_month_summary(db, DEFAULT_USER_ID)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spent Today", f"₹{summary['today_spent']:.0f}", f"{summary['today_transactions']} txns")
    c2.metric("Spent This Month", f"₹{summary['total_spent']:.0f}", f"{summary['transaction_count']} txns")
    c3.metric("Monthly Budget Left", f"₹{summary['total_remaining']:.0f}", f"Limit: ₹{summary['total_budget']:.0f}")
    c4.metric("Daily Budget Remaining", f"₹{summary['daily_budget_remaining']:.0f} / day")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚡ Quick Add Expense")
        categories = crud.list_categories(db, DEFAULT_USER_ID)
        category_names = [c.name for c in categories]

        with st.form("quick_add_expense_form", clear_on_submit=True):
            amount = st.number_input("Amount (₹)", min_value=1.0, max_value=500000.0, value=150.0, step=10.0)
            category_name = st.selectbox("Category", category_names)
            description = st.text_input("Description (e.g., Coffee, Lunch)")
            payment_method = st.selectbox("Payment Method", ["UPI", "Cash", "Card", "Other"])
            submitted = st.form_submit_button("Add Expense")

            if submitted:
                category = next((c for c in categories if c.name == category_name), None)
                crud.add_expense(db, DEFAULT_USER_ID, float(amount), category.id if category else None, date.today(), description or None, payment_method)
                st.success(f"Added expense: ₹{amount:.0f} for {category_name}")
                st.rerun()

    with col2:
        st.subheader("Category Spend Overview")
        category_df = analytics.get_category_breakdown_df(db, DEFAULT_USER_ID)
        fig = category_spend_pie(category_df)
        if fig:
            # Suppress the chart's own internal title here — the
            # st.subheader above already says essentially the same thing,
            # and stacking both crowded the top of the chart.
            fig.update_layout(title=None, margin=dict(l=20, r=20, t=20, b=70))
            st.plotly_chart(fig, use_container_width=True, key="fin_overview_cat_pie")
        else:
            ui_components.empty_state("No expenses logged this month yet.")


def _render_expenses_tab(db):
    st.subheader("Expense Management")

    col_add, col_list = st.columns([1, 2])

    with col_add:
        st.markdown("##### Log Expense")
        categories = crud.list_categories(db, DEFAULT_USER_ID)
        category_names = [c.name for c in categories]

        with st.form("add_expense_full_form", clear_on_submit=True):
            amount = st.number_input("Amount (₹)", min_value=1.0, max_value=500000.0, value=250.0, step=10.0)
            category_name = st.selectbox("Category", category_names)
            expense_date = st.date_input("Date", value=date.today())
            description = st.text_input("Description")
            payment_method = st.selectbox("Payment Method", ["UPI", "Cash", "Card", "Other"])
            submitted = st.form_submit_button("Save Expense")

            if submitted:
                category = next((c for c in categories if c.name == category_name), None)
                crud.add_expense(db, DEFAULT_USER_ID, float(amount), category.id if category else None, expense_date, description or None, payment_method)
                st.success("Expense saved!")
                st.rerun()

    with col_list:
        st.markdown("##### Expense History")
        expenses = crud.list_expenses(db, DEFAULT_USER_ID, limit=50)
        if not expenses:
            ui_components.empty_state("No expenses logged yet.")
            return

        for exp in expenses:
            c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
            c1.write(f"**{exp.expense_date}**")
            c2.write(f"**₹{exp.amount:.0f}** — {exp.category.name if exp.category else 'General'}")
            c3.caption(f"{exp.description or ''} ({exp.payment_method or 'UPI'})")
            if c4.button("🗑️", key=f"del_exp_{exp.id}"):
                crud.delete_expense(db, exp.id)
                st.rerun()


def _render_budget_tab(db):
    st.subheader("Monthly Category Budgets")

    over_budget = analytics.get_over_budget_categories(db, DEFAULT_USER_ID)
    for row in over_budget:
        st.error(f"⚠️ **{row['category_name']}** is ₹{row['overspend']:.0f} over budget "
                 f"(spent ₹{row['spent']:.0f} of ₹{row['budget_limit']:.0f})")

    col_set, col_status = st.columns([1, 2])

    with col_set:
        st.markdown("##### Set Category Budget")
        categories = crud.list_categories(db, DEFAULT_USER_ID)
        category_names = [c.name for c in categories]

        with st.form("set_budget_form", clear_on_submit=True):
            category_name = st.selectbox("Category", category_names)
            limit_amount = st.number_input("Monthly Limit (₹)", min_value=100.0, max_value=500000.0, value=3000.0, step=500.0)
            submitted = st.form_submit_button("Set Category Budget")

            if submitted:
                category = next((c for c in categories if c.name == category_name), None)
                month_start = date.today().replace(day=1)
                crud.set_budget(db, DEFAULT_USER_ID, category.id, month_start, float(limit_amount))
                st.success(f"Budget set for {category_name}: ₹{limit_amount:.0f}")
                st.rerun()

    with col_status:
        st.markdown("##### Category Budget Status")
        budget_df = analytics.get_budget_remaining_df(db, DEFAULT_USER_ID)
        fig = budget_remaining_bar(budget_df)
        if fig:
            # Drop the chart's own title — the markdown header above covers it.
            fig.update_layout(title=None, margin=dict(l=20, r=20, t=20, b=40))
            st.plotly_chart(fig, use_container_width=True, key="fin_budget_rem_bar")
        else:
            ui_components.empty_state("No budgets configured for this month.")


def _render_analytics_tab(db):
    st.subheader("Finance Analytics & Spend Trends")

    insights = analytics.get_finance_insights(db, DEFAULT_USER_ID)
    if insights:
        st.markdown("##### 💡 Insights")
        for insight in insights:
            ui_components.insight_card(insight)
        st.divider()

    col1, col2 = st.columns(2)
    with col1:
        category_df = analytics.get_category_breakdown_df(db, DEFAULT_USER_ID)
        fig = category_spend_pie(category_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="fin_analytics_cat_pie")
        else:
            ui_components.empty_state("No category breakdown data yet.")

    with col2:
        trend_df = analytics.get_spend_trend_df(db, DEFAULT_USER_ID)
        fig = spend_trend_line(trend_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="fin_spend_trend_line")
        else:
            ui_components.empty_state("Not enough expense data for trend analysis yet.")

    st.divider()
    st.markdown("##### Largest Expenses")
    largest = analytics.get_largest_expenses(db, DEFAULT_USER_ID)
    if not largest:
        ui_components.empty_state("No expenses logged yet.")
    else:
        for exp in largest:
            st.write(f"₹{exp['amount']:.0f} — {exp['category_name'] or 'General'} "
                     f"({exp['description'] or 'No description'}) on {exp['expense_date']}")
