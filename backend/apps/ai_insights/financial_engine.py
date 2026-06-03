"""
Rule-based financial insights engine.

Aggregates Income, Expense, and ROSCA data for a target month/year
using optimized Django ORM queries, then generates actionable insight cards.
"""

from datetime import date

from django.db.models import Sum
from django.utils import timezone

from apps.expenses.models import Expense, IncomeHistory
from apps.rosca.models import DrawWinner, Participant, PaymentRecord


def _to_float(value):
    return float(value) if value else 0.0


def resolve_period(month=None, year=None):
    """Return a validated (month, year) tuple, defaulting to the current period."""
    today = timezone.localdate()
    try:
        month = int(month) if month is not None else today.month
        year = int(year) if year is not None else today.year
        if not (1 <= month <= 12) or year < 2000 or year > 2100:
            raise ValueError
    except (TypeError, ValueError):
        month, year = today.month, today.year
    return month, year


def aggregate_financial_data(user, month=None, year=None):
    """
    Aggregate all financial metrics for *user* in the target month/year.

    All monetary totals use ``.aggregate(Sum('amount'))`` (or Sum on prize_amount).
    """
    month, year = resolve_period(month, year)

    standard_income = _to_float(
        IncomeHistory.objects.filter(
            user=user,
            effective_from__year=year,
            effective_from__month=month,
        ).aggregate(total=Sum("amount"))["total"]
    )

    rosca_payout = _to_float(
        DrawWinner.objects.filter(
            participant__user=user,
            month=month,
            year=year,
        ).aggregate(total=Sum("prize_amount"))["total"]
    )

    total_income = standard_income + rosca_payout

    expense_qs = Expense.objects.filter(
        user=user,
        date__year=year,
        date__month=month,
    )

    total_expenses = _to_float(
        expense_qs.aggregate(total=Sum("amount"))["total"]
    )

    expenses_by_category = [
        {
            "category": row["category"],
            "total": _to_float(row["total"]),
        }
        for row in expense_qs.values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    ]

    rosca_contributions = _to_float(
        PaymentRecord.objects.filter(
            participant__user=user,
            month=month,
            year=year,
            status=PaymentRecord.STATUS_SUCCESS,
        ).aggregate(total=Sum("amount"))["total"]
    )

    total_outflows = total_expenses + rosca_contributions
    discretionary_income = total_income - total_outflows

    if total_income > 0:
        savings_rate = round((discretionary_income / total_income) * 100, 1)
    else:
        savings_rate = 0

    active_participant = (
        Participant.objects.filter(user=user, group__is_active=True)
        .select_related("group")
        .order_by("-joined_at")
        .first()
    )

    rosca_paid = False
    rosca_pending = False
    if active_participant:
        rosca_paid = active_participant.has_paid_for(month, year)
        rosca_pending = not rosca_paid

    rosca_win = (
        DrawWinner.objects.filter(
            participant__user=user,
            month=month,
            year=year,
        )
        .select_related("group", "participant")
        .first()
    )

    is_empty = (
        total_income == 0
        and total_expenses == 0
        and rosca_contributions == 0
        and not active_participant
    )

    return {
        "month": month,
        "year": year,
        "period_label": date(year, month, 1).strftime("%B %Y"),
        "standard_income": round(standard_income, 2),
        "rosca_payout": round(rosca_payout, 2),
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "expenses_by_category": expenses_by_category,
        "rosca_contributions": round(rosca_contributions, 2),
        "total_outflows": round(total_outflows, 2),
        "discretionary_income": round(discretionary_income, 2),
        "savings_rate": savings_rate,
        "active_rosca_participant": active_participant,
        "rosca_pending": rosca_pending,
        "rosca_win": rosca_win,
        "is_empty": is_empty,
    }


def generate_rule_insights(data):
    """
    Build an ordered list of insight dicts: ``{'type': ..., 'message': ...}``.

    Types: ``danger``, ``warning``, ``success``, ``info``.
    """
    if data["is_empty"]:
        return [
            {
                "type": "info",
                "message": (
                    f"No financial records found for {data['period_label']}. "
                    "Start by logging your income, tracking expenses, or joining a ROSCA "
                    "committee to unlock personalized insights."
                ),
            }
        ]

    insights = []

    # Deficit alert
    if data["discretionary_income"] < 0:
        deficit = abs(data["discretionary_income"])
        insights.append(
            {
                "type": "danger",
                "message": (
                    f"Deficit spending alert: you are Rs. {deficit:,.0f} over budget for "
                    f"{data['period_label']}. Your outflows exceed income — review expenses "
                    "immediately and avoid dipping into past savings."
                ),
            }
        )

    # ROSCA pending (high priority — before softer warnings)
    if data["rosca_pending"]:
        due = data["active_rosca_participant"].group.monthly_contribution
        group_name = data["active_rosca_participant"].group.name
        insights.append(
            {
                "type": "danger",
                "message": (
                    f"ROSCA payment overdue: your {group_name} contribution of "
                    f"Rs. {float(due):,.0f} for {data['period_label']} is unpaid. "
                    "Pay now to stay eligible for this month's draw."
                ),
            }
        )

    # Winner's advice
    if data["rosca_win"]:
        prize = float(data["rosca_win"].prize_amount)
        insights.append(
            {
                "type": "success",
                "message": (
                    f"You received your ROSCA payout of Rs. {prize:,.0f} from "
                    f"{data['rosca_win'].group.name}! Consider allocating at least 50% "
                    "toward savings or investments rather than inflating lifestyle expenses."
                ),
            }
        )

    # Category anomaly
    if data["total_income"] > 0 and data["expenses_by_category"]:
        top = data["expenses_by_category"][0]
        share = (top["total"] / data["total_income"]) * 100
        if share > 40:
            insights.append(
                {
                    "type": "warning",
                    "message": (
                        f"Your '{top['category']}' expenses are taking up {share:.0f}% of "
                        f"your income this month. Consider a budget review to rebalance "
                        "your spending."
                    ),
                }
            )

    # Positive savings note when healthy and no other success insight
    if (
        data["discretionary_income"] > 0
        and data["savings_rate"] >= 20
        and not data["rosca_win"]
    ):
        insights.append(
            {
                "type": "success",
                "message": (
                    f"Strong financial health: you kept a {data['savings_rate']:.1f}% "
                    f"savings rate in {data['period_label']} with Rs. "
                    f"{data['discretionary_income']:,.0f} in free cash after expenses and dues."
                ),
            }
        )

    if not insights:
        insights.append(
            {
                "type": "info",
                "message": (
                    f"Your finances for {data['period_label']} look balanced. "
                    "Keep logging transactions to receive deeper, personalized guidance."
                ),
            }
        )

    return insights


def build_financial_insights(user, month=None, year=None):
    """Full pipeline: aggregate data then generate rule-based insights."""
    data = aggregate_financial_data(user, month, year)
    insights = generate_rule_insights(data)
    return {"metrics": data, "insights": insights}
