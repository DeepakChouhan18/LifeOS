"""
Finance module analytics.

Turns raw DB rows (from database/raw_queries.py) into financial metrics:
today's spend, monthly spend, category breakdown, budget remaining, spend trend.
"""

from datetime import date
import pandas as pd

from database import raw_queries as rq
from modules.settings import crud as settings_crud
from utils import date_helpers


def _current_month_str() -> str:
    return date.today().strftime("%Y-%m")


def get_current_month_summary(session, user_id: int) -> dict:
    month = _current_month_str()
    today_date = date.today()

    today_summary = rq.get_today_spend(session, user_id, today_date)
    monthly = rq.get_monthly_spend(session, user_id)
    this_month = next((m for m in monthly if m["month"] == month), None)

    total_spent = this_month["total_spent"] if this_month else 0.0
    transaction_count = this_month["transaction_count"] if this_month else 0

    budget_rows = rq.get_budget_remaining(session, user_id, month)
    total_budget = sum(b["budget_limit"] for b in budget_rows) if budget_rows else 0.0
    total_remaining = sum(b["remaining"] for b in budget_rows) if budget_rows else 0.0

    # If no category budgets set, fallback to user's monthly_budget preference from profile
    if total_budget == 0.0:
        profile = settings_crud.get_user_profile(session, user_id)
        if profile and profile.monthly_budget:
            # profile.monthly_budget is read via the ORM from a Numeric(10,2)
            # column, so SQLAlchemy returns it as a Decimal. Everything else
            # here (total_spent, etc.) comes from raw SQL and is a plain
            # float. Python won't do arithmetic across Decimal and float,
            # so cast to float immediately at the point of reading it.
            total_budget = float(profile.monthly_budget)
            total_remaining = total_budget - total_spent

    # Daily remaining budget calculation
    days_in_month = date_helpers.days_in_current_month()
    days_left = max(1, days_in_month - date_helpers.days_elapsed_in_month() + 1)
    daily_budget_remaining = max(0.0, total_remaining / days_left)

    return {
        "today_spent": today_summary["today_spent"],
        "today_transactions": today_summary["today_transactions"],
        "total_spent": total_spent,
        "transaction_count": transaction_count,
        "total_budget": total_budget,
        "total_remaining": total_remaining,
        "daily_budget_remaining": round(daily_budget_remaining, 2),
    }


def get_category_breakdown_df(session, user_id: int, month: str = None) -> pd.DataFrame:
    month = month or _current_month_str()
    rows = rq.get_category_breakdown(session, user_id, month)
    return pd.DataFrame(rows)


def get_budget_remaining_df(session, user_id: int, month: str = None) -> pd.DataFrame:
    month = month or _current_month_str()
    rows = rq.get_budget_remaining(session, user_id, month)
    return pd.DataFrame(rows)


def get_spend_trend_df(session, user_id: int) -> pd.DataFrame:
    rows = rq.get_rolling_spend(session, user_id)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["expense_date"] = pd.to_datetime(df["expense_date"])
    return df


def get_full_summary(session, user_id: int) -> dict:
    """One call that returns everything the dashboard page needs."""
    summary = get_current_month_summary(session, user_id)
    return {
        "today_spent": summary["today_spent"],
        "total_spent_this_month": summary["total_spent"],
        "total_budget_this_month": summary["total_budget"],
        "budget_remaining": summary["total_remaining"],
        "daily_budget_remaining": summary["daily_budget_remaining"],
        "transaction_count": summary["transaction_count"],
    }


def get_over_budget_categories(session, user_id: int) -> list:
    """Categories where spend has exceeded budget this month (SQL HAVING clause)."""
    return rq.get_over_budget_categories(session, user_id, _current_month_str())


def get_largest_expenses(session, user_id: int, limit: int = 5) -> list:
    return rq.get_largest_expenses(session, user_id, limit)


def get_finance_insights(session, user_id: int) -> list:
    """
    Generates plain-language insights purely from real stored data —
    never hard-coded. Each insight is only included if the underlying
    data actually supports it (e.g. month-over-month comparison is
    skipped entirely if last month has no data to compare against).
    """
    insights = []
    today = date.today()
    this_month = today.strftime("%Y-%m")
    last_month_date = (today.replace(day=1) - pd_offset_one_day())
    last_month = last_month_date.strftime("%Y-%m")

    # Month-over-month category change
    mom_rows = rq.get_month_over_month_category(session, user_id, this_month, last_month)
    for row in mom_rows:
        last = float(row["last_month_spent"])
        this = float(row["this_month_spent"])
        if last > 0 and this > 0:
            pct_change = ((this - last) / last) * 100
            if abs(pct_change) >= 15:  # only surface meaningful changes
                direction = "increased" if pct_change > 0 else "decreased"
                insights.append(
                    f"{row['category_name']} spending {direction} "
                    f"{abs(pct_change):.0f}% compared with last month."
                )

    # Highest spending weekday
    weekday_rows = rq.get_spending_by_weekday(session, user_id)
    if weekday_rows and len(weekday_rows) >= 3:  # need a few weeks of variety for this to mean anything
        top = weekday_rows[0]
        insights.append(f"Your highest spending day has been {top['weekday_name']}.")

    # Over-budget categories
    over_budget = get_over_budget_categories(session, user_id)
    for row in over_budget:
        insights.append(
            f"You're ₹{row['overspend']:.0f} over budget in {row['category_name']} this month."
        )

    return insights[:5]  # keep the Overview page focused, not a wall of text


def pd_offset_one_day():
    from datetime import timedelta
    return timedelta(days=1)
