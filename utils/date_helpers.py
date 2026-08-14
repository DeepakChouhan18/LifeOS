"""
Date and time helpers shared across modules.
"""

from datetime import date, timedelta, datetime


def greeting() -> str:
    """Returns a time-appropriate greeting."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"


def today() -> date:
    return date.today()


def week_start(d: date = None) -> date:
    """Monday of the week containing `d`."""
    d = d or date.today()
    return d - timedelta(days=d.weekday())


def week_end(d: date = None) -> date:
    """Sunday of the week containing `d`."""
    return week_start(d) + timedelta(days=6)


def month_start(d: date = None) -> date:
    d = d or date.today()
    return d.replace(day=1)


def current_month_str(d: date = None) -> str:
    """Returns 'YYYY-MM' for the given or current date."""
    d = d or date.today()
    return d.strftime("%Y-%m")


def format_date(d) -> str:
    """Human-friendly date format."""
    if isinstance(d, str):
        d = datetime.strptime(d, "%Y-%m-%d").date()
    if d == date.today():
        return "Today"
    elif d == date.today() - timedelta(days=1):
        return "Yesterday"
    return d.strftime("%b %d, %Y")


def format_minutes(minutes: int) -> str:
    """Formats minutes as 'Xh Ym'."""
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    remaining = minutes % 60
    if remaining == 0:
        return f"{hours}h"
    return f"{hours}h {remaining}m"


def days_in_current_month() -> int:
    """Number of days in the current month."""
    d = date.today()
    if d.month == 12:
        next_month = d.replace(year=d.year + 1, month=1, day=1)
    else:
        next_month = d.replace(month=d.month + 1, day=1)
    return (next_month - d.replace(day=1)).days


def days_elapsed_in_month() -> int:
    """Days elapsed so far in the current month (including today)."""
    return date.today().day


def today_label() -> str:
    """Returns a human-friendly today string, e.g. 'Thu, Aug 14'."""
    return date.today().strftime("%a, %b %d")

