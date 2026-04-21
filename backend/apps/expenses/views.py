from django.http import JsonResponse
from django.shortcuts import render
from .models import Expense
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
import json


def home(request):
    return render(request, 'index.html')


@csrf_exempt
def expenses_list(request):

    # ✅ GET ALL EXPENSES
    if request.method == "GET":
        expenses = list(Expense.objects.values())
        return JsonResponse(expenses, safe=False)

    # ✅ CREATE EXPENSE
    elif request.method == "POST":
        try:
            data = json.loads(request.body)

            amount = float(data.get("amount"))

            # ✅ VALIDATION
            if amount <= 0:
                return JsonResponse({"error": "Amount must be positive"}, status=400)

            Expense.objects.create(
                amount=amount,
                category=data.get("category"),
                payment_method=data.get("paymentMethod"),
                where_spent=data.get("whereSpent"),
                date=data.get("date"),
                time=data.get("time") or None,
            )

            return JsonResponse({"message": "Expense added"}, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def delete_expense(request, id):
    if request.method == "DELETE":
        Expense.objects.filter(id=id).delete()
        return JsonResponse({"message": "Deleted"})


# ✅ INSIGHTS (still basic for now)
def insights(request):
    expenses = Expense.objects.all()

    total = expenses.aggregate(Sum("amount"))["amount__sum"] or 0

    personal = expenses.filter(category="Personal").aggregate(Sum("amount"))["amount__sum"] or 0
    professional = expenses.filter(category="Professional").aggregate(Sum("amount"))["amount__sum"] or 0

    if personal > professional:
        insight = "You are spending more on PERSONAL expenses."
    elif professional > personal:
        insight = "You are spending more on PROFESSIONAL expenses."
    else:
        insight = "Balanced spending."

    return JsonResponse({
        "total": total,
        "personal": personal,
        "professional": professional,
        "insight": insight
    })