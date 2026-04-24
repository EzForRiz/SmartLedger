import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Sum
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

            payment_method = data.get("payment_method")
            if payment_method not in ("cash", "card", "easypaisa", "jazzcash"):
                return JsonResponse({"error": "Invalid payment method"}, status=400)

            where_spent = (data.get("where_spent") or "").strip()
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
def insights(request):
    expenses = Expense.objects.all()

    total = expenses.aggregate(Sum("amount"))["amount__sum"] or 0
    personal = expenses.filter(category="Personal").aggregate(Sum("amount"))["amount__sum"] or 0
    professional = expenses.filter(category="Professional").aggregate(Sum("amount"))["amount__sum"] or 0

    if total == 0:
        insight = "No expenses recorded yet."
    elif personal > professional:
        insight = f"Personal spending is higher ({round(personal/total*100)}%)."
    else:
        insight = f"Professional spending is higher ({round(professional/total*100)}%)."

    return JsonResponse({
        "total": round(total, 2),
        "personal": round(personal, 2),
        "professional": round(professional, 2),
        "insight": insight
    })


def dashboard(request):
    return render(request, 'dashboard.html')


def rosca(request):
    return render(request, 'rosca.html')