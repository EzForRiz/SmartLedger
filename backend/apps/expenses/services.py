# backend/apps/expenses/services.py

from django.db.models import Sum
from .models import Expense, IncomeHistory


def get_income_for_month(user, month_date):
    """
    Returns total income for the given calendar month
    (sum of all entries whose effective_from falls in that month).
    """

    total = (
        IncomeHistory.objects
        .filter(
            user=user,
            effective_from__year=month_date.year,
            effective_from__month=month_date.month,
        )
        .aggregate(total=Sum("amount"))["total"]
    )

    return float(total) if total else 0


def get_monthly_finance(user, month_date):

    expenses = Expense.objects.filter(
        user=user,
        date__year=month_date.year,
        date__month=month_date.month
    )

    total_expenses = (
        expenses.aggregate(total=Sum("amount"))["total"]
        or 0
    )

    total_expenses = float(total_expenses)

    income = get_income_for_month(user, month_date)

    budget = income - total_expenses

    savings_rate = 0

    if income > 0:
        savings_rate = round((budget / income) * 100, 1)

    return {
        "income": income,
        "expenses": total_expenses,
        "budget": budget,
        "savings_rate": savings_rate
    }