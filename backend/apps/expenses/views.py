from django.http import JsonResponse
from django.shortcuts import render
from .models import Expense
import json
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum


def home(request):
    return render(request, 'index.html')


@csrf_exempt
def expenses_list(request):
    if request.method == 'GET':
        expenses = list(Expense.objects.values())
        return JsonResponse(expenses, safe=False)

    elif request.method == 'POST':
        data = json.loads(request.body)

        Expense.objects.create(
            date=data.get('date'),
            time=data.get('time') or None,
            amount=data.get('amount'),
            where_spent=data.get('whereSpent'),
            payment_method=data.get('paymentMethod'),
            use_type=data.get('useType'),
        )

        return JsonResponse({"message": "Expense added"}, status=201)


@csrf_exempt
def delete_expense(request, id):
    if request.method == 'DELETE':
        Expense.objects.filter(id=id).delete()
        return JsonResponse({"message": "Deleted"})


def insights(request):
    expenses = Expense.objects.all()

    total = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    personal = expenses.filter(use_type="Personal").aggregate(Sum('amount'))['amount__sum'] or 0
    professional = expenses.filter(use_type="Professional").aggregate(Sum('amount'))['amount__sum'] or 0

    if personal > professional:
        insight = "You are spending more on PERSONAL expenses. Try controlling lifestyle costs."
    elif professional > personal:
        insight = "Your PROFESSIONAL spending is higher. Monitor business expenses."
    else:
        insight = "Your spending is balanced across categories."

    return JsonResponse({
        "total": total,
        "personal": personal,
        "professional": professional,
        "insight": insight
    })