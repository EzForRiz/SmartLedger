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
    if request.method == "GET":
        expenses = list(Expense.objects.values())
        return JsonResponse(expenses, safe=False)

    elif request.method == "POST":
        data = json.loads(request.body)

        Expense.objects.create(
            amount=data.get("amount"),
            category=data.get("category"),
            payment_method=data.get("paymentMethod"),
            where_spent=data.get("whereSpent"),
            time=data.get("time") or None,
        )

        return JsonResponse({"message": "Expense added"}, status=201)


@csrf_exempt
def delete_expense(request, id):
    if request.method == "DELETE":
        Expense.objects.filter(id=id).delete()
        return JsonResponse({"message": "Deleted"})


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