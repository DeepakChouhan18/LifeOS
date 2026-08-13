"""
ORM-based CRUD operations for the Finance module.
Includes expense management with edit/delete, category management, and budget limits.
"""

from datetime import date
from database.models import ExpenseCategory, Expense, Budget
from utils import validation


def get_or_create_category(session, user_id: int, name: str) -> ExpenseCategory:
    category = (
        session.query(ExpenseCategory)
        .filter_by(user_id=user_id, name=name)
        .first()
    )
    if category:
        return category
    category = ExpenseCategory(user_id=user_id, name=name)
    session.add(category)
    session.commit()
    return category


def list_categories(session, user_id: int):
    return session.query(ExpenseCategory).filter_by(user_id=user_id).order_by(ExpenseCategory.name).all()


def add_expense(
    session, user_id: int, amount: float, category_id: int = None,
    expense_date: date = None, description: str = None, payment_method: str = None
) -> Expense:
    validation.validate_expense_amount(amount)
    validation.validate_not_future_date(expense_date, "Expense date")
    expense = Expense(
        user_id=user_id,
        category_id=category_id,
        amount=amount,
        expense_date=expense_date or date.today(),
        description=description,
        payment_method=payment_method or "UPI",
    )
    session.add(expense)
    session.commit()
    return expense


def update_expense(
    session, expense_id: int, amount: float = None, category_id: int = None,
    expense_date: date = None, description: str = None, payment_method: str = None
) -> Expense:
    expense = session.get(Expense, expense_id)
    if expense:
        if amount is not None:
            expense.amount = amount
        if category_id is not None:
            expense.category_id = category_id
        if expense_date is not None:
            expense.expense_date = expense_date
        if description is not None:
            expense.description = description
        if payment_method is not None:
            expense.payment_method = payment_method
        session.commit()
    return expense


def delete_expense(session, expense_id: int) -> bool:
    expense = session.get(Expense, expense_id)
    if expense:
        session.delete(expense)
        session.commit()
        return True
    return False


def list_expenses(session, user_id: int, limit: int = 100):
    return (
        session.query(Expense)
        .filter_by(user_id=user_id)
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .limit(limit)
        .all()
    )


def set_budget(session, user_id: int, category_id: int, month: date, limit_amount: float) -> Budget:
    """Creates or updates the budget for a given category + month."""
    # Ensure month is first-of-month
    month_start = month.replace(day=1)
    existing = (
        session.query(Budget)
        .filter_by(user_id=user_id, category_id=category_id, month=month_start)
        .first()
    )
    if existing:
        existing.limit_amount = limit_amount
        session.commit()
        return existing

    budget = Budget(user_id=user_id, category_id=category_id, month=month_start, limit_amount=limit_amount)
    session.add(budget)
    session.commit()
    return budget


def delete_budget(session, budget_id: int) -> bool:
    b = session.get(Budget, budget_id)
    if b:
        session.delete(b)
        session.commit()
        return True
    return False


def list_budgets(session, user_id: int, month: date = None):
    query = session.query(Budget).filter_by(user_id=user_id)
    if month:
        query = query.filter_by(month=month.replace(day=1))
    return query.all()
