"""
Streamlit UI for the Finance module.

Features:
- Overview: today's spending, monthly summary, quick add, category pie chart
- Expenses: full expense history with delete
- Budgets: set monthly limits, visual progress bars
- Analytics: spend trends, insights, largest expenses
"""

import streamlit as st
from datetime import date

from database.connection import get_session
from database import cache
from modules.finance import crud, analytics
from utils.charts import category_spend_pie, budget_remaining_bar, spend_trend_line
from utils import ui_components, date_helpers
from config import DEFAULT_EXPENSE_CATEGORIES


def render(user_id: int):
    ui_components.page_header(
        "Finance",
        "Track daily expenses, manage monthly budgets, and analyze spending patterns.",
    )

    db = get_session()
    try:
        _ensure_default_categories(db, user_id)

        tab_overview, tab_expenses, tab_budget, tab_analytics = st.tabs([
            "Overview", "Expenses", "Budgets", "Analytics"
        ])

        with tab_overview:
            _render_overview_tab(db, user_id)
        with tab_expenses:
            _render_expenses_tab(db, user_id)
        with tab_budget:
            _render_budget_tab(db, user_id)
        with tab_analytics:
            _render_analytics_tab(user_id)

    finally:
        db.close()


def _ensure_default_categories(db, user_id: int):
    created_any = False
    for name in DEFAULT_EXPENSE_CATEGORIES:
        result = crud.get_or_create_category(db, user_id, name)
        # get_or_create_category returns the category; we can't easily detect
        # "was it created?" without inspecting the object, so always refresh.
    # Flush the categories cache so any newly created defaults appear immediately.
    cache.get_finance_categories.clear()


# =======================================================================
# OVERVIEW TAB
# =======================================================================

def _render_overview_tab(db, user_id: int):
    summary = cache.get_finance_current_month_summary(user_id)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui_components.metric_card(
            "Spent Today", f"₹{summary['today_spent']:.0f}",
            subtitle=f"{summary['today_transactions']} transaction(s)",
            accent_color="#f59e0b",
        )
    with c2:
        ui_components.metric_card(
            "This Month", f"₹{summary['total_spent']:.0f}",
            subtitle=f"{summary['transaction_count']} transactions",
            accent_color="#f59e0b",
        )
    with c3:
        ui_components.metric_card(
            "Budget Remaining", f"₹{summary['total_remaining']:.0f}",
            subtitle=f"Limit ₹{summary['total_budget']:.0f}",
            accent_color="#f59e0b",
        )
    with c4:
        ui_components.metric_card(
            "Daily Budget Left", f"₹{summary['daily_budget_remaining']:.0f}/day",
            subtitle="Over remaining days this month",
            accent_color="#f59e0b",
        )

    st.markdown("<hr style='border-color:#1a2540;margin:1.25rem 0;'>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        ui_components.section_header("QUICK ADD EXPENSE")
        categories = cache.get_finance_categories(user_id)
        category_names = [c["name"] for c in categories]

        with st.form("quick_add_expense_form", clear_on_submit=True):
            amount = st.number_input("Amount (₹)", min_value=1.0, max_value=500000.0, value=150.0, step=10.0)
            category_name = st.selectbox("Category", category_names)
            description = st.text_input("Description", placeholder="What did you buy?")
            payment_method = st.selectbox("Payment", ["UPI", "Cash", "Card", "Other"])
            submitted = st.form_submit_button("+ Add Expense", type="primary", use_container_width=True)

            if submitted:
                category = next((c for c in categories if c["name"] == category_name), None)
                crud.add_expense(db, user_id, float(amount), category["id"] if category else None,
                                  date.today(), description or None, payment_method)
                cache.clear_after_expense_write()
                st.success(f"Added ₹{amount:.0f} for {category_name}.")
                st.rerun()

    with col2:
        category_df = cache.get_finance_category_breakdown(user_id)
        fig = category_spend_pie(category_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="fin_overview_cat_pie")
        else:
            ui_components.empty_state(
                "No spending logged this month",
                icon="",
                hint="Log your first expense on the left to populate the chart.",
            )


# =======================================================================
# EXPENSES TAB
# =======================================================================

def _render_expenses_tab(db, user_id: int):
    col_add, col_list = st.columns([1, 2], gap="large")

    with col_add:
        ui_components.section_header("ADD EXPENSE")
        categories = cache.get_finance_categories(user_id)
        category_names = [c["name"] for c in categories]

        with st.form("add_expense_full_form", clear_on_submit=True):
            amount = st.number_input("Amount (₹)", min_value=1.0, max_value=500000.0, value=250.0, step=10.0)
            category_name = st.selectbox("Category", category_names)
            expense_date = st.date_input("Date", value=date.today())
            description = st.text_input("Description / Notes")
            payment_method = st.selectbox("Payment Method", ["UPI", "Cash", "Card", "Other"])
            submitted = st.form_submit_button("Save Expense", type="primary", use_container_width=True)

            if submitted:
                category = next((c for c in categories if c["name"] == category_name), None)
                crud.add_expense(db, user_id, float(amount), category["id"] if category else None,
                                  expense_date, description or None, payment_method)
                cache.clear_after_expense_write()
                st.success("Expense saved.")
                st.rerun()

    with col_list:
        ui_components.section_header("HISTORY")
        expenses = cache.get_finance_expenses(user_id, limit=50)
        if not expenses:
            ui_components.empty_state(
                "No expenses logged yet",
                icon="",
                hint="Log transactions using the quick add form on the Overview tab.",
            )
            return

        for exp in expenses:
            col_info, col_del = st.columns([5, 1])
            with col_info:
                date_lbl = date_helpers.format_date(exp["expense_date"])
                desc_lbl = exp["description"] or ""
                cat_lbl = exp["category_name"]
                method_badge = ui_components.status_badge(exp["payment_method"] or "UPI", "info")
                st.markdown(
                    f'<div style="padding:0.6rem 0.8rem;background:#111927;border-radius:8px;'
                    f'margin-bottom:0.35rem;border:1px solid #1e293b;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<span style="font-weight:700;font-size:0.9rem;color:#f8fafc;">₹{exp["amount"]:.0f}</span>'
                    f'<span>{method_badge}</span>'
                    f'</div>'
                    f'<div style="font-size:0.78rem;color:#64748b;margin-top:0.1rem;">'
                    f'{date_lbl} · {cat_lbl}'
                    + (f' · {desc_lbl}' if desc_lbl else '') +
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            with col_del:
                st.markdown("<div style='margin-top:0.6rem;'></div>", unsafe_allow_html=True)
                if st.button("Delete", key=f"del_exp_{exp['id']}", use_container_width=True):
                    crud.delete_expense(db, exp["id"])
                    cache.clear_after_expense_write()
                    st.rerun()


# =======================================================================
# BUDGETS TAB
# =======================================================================

def _render_budget_tab(db, user_id: int):
    over_budget = cache.get_finance_over_budget(user_id)
    for row in over_budget:
        ui_components.info_banner(
            f"{row['category_name']} is ₹{row['overspend']:.0f} over budget "
            f"(₹{row['spent']:.0f} of ₹{row['budget_limit']:.0f})",
            banner_type="danger",
        )

    col_set, col_status = st.columns([1, 2], gap="large")

    with col_set:
        ui_components.section_header("SET BUDGET LIMIT")
        categories = cache.get_finance_categories(user_id)
        category_names = [c["name"] for c in categories]

        with st.form("set_budget_form", clear_on_submit=True):
            category_name = st.selectbox("Category", category_names)
            limit_amount = st.number_input("Monthly Limit (₹)", min_value=100.0, max_value=500000.0, value=3000.0, step=500.0)
            submitted = st.form_submit_button("Set Limit", type="primary", use_container_width=True)

            if submitted:
                category = next((c for c in categories if c["name"] == category_name), None)
                month_start = date.today().replace(day=1)
                crud.set_budget(db, user_id, category["id"], month_start, float(limit_amount))
                cache.clear_after_budget_write()
                st.success(f"Budget set for {category_name}: ₹{limit_amount:.0f}")
                st.rerun()

    with col_status:
        ui_components.section_header("BUDGET STATUS")
        budget_df = cache.get_finance_budget_remaining(user_id)
        if budget_df.empty:
            ui_components.empty_state(
                "No budgets configured for this month",
                icon="",
                hint="Set a category limit to track your spending against targets.",
            )
        else:
            for idx, row in budget_df.iterrows():
                limit = float(row["budget_limit"])
                spent = float(row["spent"])
                ui_components.budget_progress_row(row["category_name"], limit, spent)


# =======================================================================
# ANALYTICS TAB
# =======================================================================

def _render_analytics_tab(user_id: int):
    # Read-only — all data from cache, no db needed.
    insights = cache.get_finance_insights(user_id)
    if insights:
        ui_components.section_header("INSIGHTS")
        for insight in insights:
            ui_components.insight_card(insight)
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        category_df = cache.get_finance_category_breakdown(user_id)
        fig = category_spend_pie(category_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="fin_analytics_cat_pie")
        else:
            ui_components.empty_state("No category data yet", icon="")

    with col2:
        trend_df = cache.get_finance_spend_trend(user_id)
        fig = spend_trend_line(trend_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="fin_spend_trend_line")
        else:
            ui_components.empty_state("Not enough data for trend analysis", icon="")

    st.markdown("<hr style='border-color:#1a2540;margin:1.25rem 0;'>", unsafe_allow_html=True)

    ui_components.section_header("LARGEST EXPENSES THIS MONTH")
    largest = cache.get_finance_largest_expenses(user_id)
    if not largest:
        ui_components.empty_state("No expenses logged yet", icon="")
    else:
        for exp in largest:
            date_lbl = date_helpers.format_date(exp['expense_date'])
            desc_str = f" · {exp['description']}" if exp['description'] else ""
            cat_str = exp['category_name'] or "General"
            st.markdown(
                f'<div style="padding:0.55rem 0.75rem;background:#111927;border-radius:8px;'
                f'margin-bottom:0.35rem;border:1px solid #1e293b;">'
                f'<span style="font-weight:700;color:#f59e0b;font-size:0.9rem;">₹{exp["amount"]:.0f}</span> · '
                f'<span style="font-size:0.875rem;color:#e2e8f0;font-weight:500;">{cat_str}</span>'
                f'<span style="font-size:0.78rem;color:#64748b;"> · {date_lbl}{desc_str}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
