from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .financial_engine import build_financial_insights, resolve_period


def _picker_context(selected_month, selected_year):
    today = timezone.localdate()
    years = list(range(today.year, today.year - 3, -1))
    months = [
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December"),
    ]
    return {
        "months": months,
        "years": years,
        "selected_month": selected_month,
        "selected_year": selected_year,
    }


@login_required
def insights_hub(request):
    month, year = resolve_period(
        request.GET.get("month"),
        request.GET.get("year"),
    )
    result = build_financial_insights(request.user, month, year)
    metrics = result["metrics"]

    context = {
        "metrics": metrics,
        "insights": result["insights"],
        **_picker_context(month, year),
    }
    return render(request, "financial_insights.html", context)


@login_required
def insights_analysis_api(request):
    """JSON endpoint for the financial insights engine."""
    month, year = resolve_period(
        request.GET.get("month"),
        request.GET.get("year"),
    )
    result = build_financial_insights(request.user, month, year)
    metrics = result["metrics"].copy()

    # Serialize non-JSON-safe objects
    metrics["active_rosca_participant"] = bool(metrics["active_rosca_participant"])
    if metrics["rosca_win"]:
        win = metrics["rosca_win"]
        metrics["rosca_win"] = {
            "group": win.group.name,
            "prize_amount": float(win.prize_amount),
        }
    else:
        metrics["rosca_win"] = None

    return JsonResponse(
        {
            "success": True,
            "data": {
                "metrics": metrics,
                "insights": result["insights"],
            },
        }
    )
