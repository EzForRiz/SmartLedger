# backend/expenses/services.py

from django.db.models import Sum
from .models import Expense, IncomeHistory


def get_income_for_month(user, month_date):
    """
    Returns active income for given month.
    """

    income = (
        IncomeHistory.objects
        .filter(
            user=user,
            effective_from__lte=month_date
        )
        .order_by("-effective_from")
        .first()
    )

    return float(income.amount) if income else 0


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