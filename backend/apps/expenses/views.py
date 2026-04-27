# apps/expenses/views.py

import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Expense


def home(request):
    return render(request, 'index.html')


@csrf_exempt
@require_http_methods(["GET", "POST"])
def expenses_list(request):

    # ───────────────── GET ─────────────────
    if request.method == "GET":
        expenses = list(Expense.objects.values(
            'id', 'date', 'time', 'amount', 'category',
            'where_spent', 'payment_method'
        ))

        for e in expenses:
            e['date'] = str(e['date'])
            e['time'] = str(e['time']) if e['time'] else None

        return JsonResponse(expenses, safe=False)

    # ───────────────── POST ─────────────────
    elif request.method == "POST":
        try:
            data = json.loads(request.body)

            amount = float(data.get("amount", 0))
            if amount <= 0:
                return JsonResponse({"error": "Invalid amount"}, status=400)

            category = data.get("category")
            if category not in ("Personal", "Professional"):
                return JsonResponse({"error": "Invalid category"}, status=400)

            payment_method = data.get("paymentMethod")
            if payment_method not in ("cash", "card", "easypaisa", "jazzcash"):
                return JsonResponse({"error": "Invalid payment method"}, status=400)

            where_spent = (data.get("whereSpent") or "").strip()
            if not where_spent:
                return JsonResponse({"error": "Where spent is required"}, status=400)

            date = data.get("date")
            if not date:
                return JsonResponse({"error": "Date is required"}, status=400)

            time_val = data.get("time") or None

            expense = Expense.objects.create(
                amount=amount,
                category=category,
                payment_method=payment_method,
                where_spent=where_spent,
                date=date,
                time=time_val,
            )

            return JsonResponse({
                "message": "Expense added",
                "id": expense.id
            }, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


# ───────────────── DELETE ─────────────────
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_expense(request, id):
    deleted, _ = Expense.objects.filter(id=id).delete()

    if deleted:
        return JsonResponse({"message": "Deleted"})

    return JsonResponse({"error": "Not found"}, status=404)


# ───────────────── INSIGHTS ─────────────────
from apps.ai_insights.services import generate_insights

def insights(request):
    expenses = Expense.objects.all()

    data = generate_insights(expenses)

    return JsonResponse(data)


def dashboard(request):
    return render(request, 'dashboard.html')


def rosca(request):
    return render(request, 'rosca.html')