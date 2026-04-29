# apps/expenses/views.py

import json
from datetime import date as date_type
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

    if request.method == "GET":
        expenses = list(Expense.objects.values(
            'id', 'date', 'time', 'amount', 'category',
            'where_spent', 'payment_method'
        ))
        for e in expenses:
            e['date'] = str(e['date'])
            e['amount'] = float(e['amount'])
            # Only show HH:MM not seconds
            e['time'] = str(e['time'])[:5] if e['time'] else None
        return JsonResponse(expenses, safe=False)

    elif request.method == "POST":
        try:
            data = json.loads(request.body)

            amount = float(data.get("amount", 0))
            if amount <= 0:
                return JsonResponse({"error": "Amount must be positive"}, status=400)
            if amount > 9999999:
                return JsonResponse({"error": "Amount is too large"}, status=400)

            category = data.get("category")
            if category not in ("Personal", "Professional"):
                return JsonResponse({"error": "Invalid category"}, status=400)

            payment_method = data.get("paymentMethod")
            if payment_method not in ("cash", "card", "easypaisa", "jazzcash"):
                return JsonResponse({"error": "Invalid payment method"}, status=400)

            # Normalize where_spent — trim + title case
            where_spent = (data.get("whereSpent") or "").strip().title()
            if not where_spent:
                return JsonResponse({"error": "Where spent is required"}, status=400)

            date_str = data.get("date")
            if not date_str:
                return JsonResponse({"error": "Date is required"}, status=400)

            # Reject future dates
            from datetime import date as date_type
            from datetime import datetime
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"error": "Invalid date format"}, status=400)

            if parsed_date > date_type.today():
                return JsonResponse({"error": "Date cannot be in the future"}, status=400)

            time_val = data.get("time") or None

            expense = Expense.objects.create(
                amount=amount,
                category=category,
                payment_method=payment_method,
                where_spent=where_spent,
                date=date_str,
                time=time_val,
            )

            return JsonResponse({"message": "Expense added", "id": expense.id}, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["DELETE", "PUT"])
def expense_detail(request, id):

    if request.method == "DELETE":
        deleted, _ = Expense.objects.filter(id=id).delete()
        if deleted:
            return JsonResponse({"message": "Deleted"})
        return JsonResponse({"error": "Not found"}, status=404)

    elif request.method == "PUT":
        try:
            expense = Expense.objects.get(id=id)
        except Expense.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        try:
            data = json.loads(request.body)

            amount = float(data.get("amount", 0))
            if amount <= 0:
                return JsonResponse({"error": "Amount must be positive"}, status=400)
            if amount > 9999999:
                return JsonResponse({"error": "Amount is too large"}, status=400)

            category = data.get("category")
            if category not in ("Personal", "Professional"):
                return JsonResponse({"error": "Invalid category"}, status=400)

            payment_method = data.get("paymentMethod")
            if payment_method not in ("cash", "card", "easypaisa", "jazzcash"):
                return JsonResponse({"error": "Invalid payment method"}, status=400)

            # Normalize where_spent
            where_spent = (data.get("whereSpent") or "").strip().title()
            if not where_spent:
                return JsonResponse({"error": "Where spent is required"}, status=400)

            date_str = data.get("date")
            if not date_str:
                return JsonResponse({"error": "Date is required"}, status=400)

            from datetime import datetime
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"error": "Invalid date format"}, status=400)

            if parsed_date > date_type.today():
                return JsonResponse({"error": "Date cannot be in the future"}, status=400)

            expense.amount = amount
            expense.category = category
            expense.payment_method = payment_method
            expense.where_spent = where_spent
            expense.date = date_str
            expense.time = data.get("time") or None
            expense.save()

            return JsonResponse({"message": "Expense updated", "id": expense.id})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


from apps.ai_insights.services import generate_insights

def insights(request):
    expenses = Expense.objects.all()
    data = generate_insights(expenses)
    return JsonResponse(data)


def dashboard(request):
    return render(request, 'dashboard.html')


def rosca(request):
    return render(request, 'rosca.html')