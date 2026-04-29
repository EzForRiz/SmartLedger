# apps/expenses/views.py

import json
from datetime import date as date_type, datetime
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Expense
from apps.ai_insights.services import generate_insights


# ───────────────── AUTH ─────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('/')
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('/')
        else:
            error = "Invalid username or password"
    return render(request, 'login.html', {"error": error})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('/')
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm_password", "")
        if not username or not password:
            error = "All fields are required"
        elif len(password) < 6:
            error = "Password must be at least 6 characters"
        elif password != confirm:
            error = "Passwords do not match"
        elif User.objects.filter(username=username).exists():
            error = "Username already taken"
        else:
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            return redirect('/')
    return render(request, 'register.html', {"error": error})


def logout_view(request):
    logout(request)
    return redirect('/login/')


# ───────────────── PAGES ─────────────────

@login_required
def home(request):
    return render(request, 'index.html')


@login_required
def dashboard(request):
    return render(request, 'dashboard.html')


@login_required
def rosca(request):
    return render(request, 'rosca.html')


# ───────────────── EXPENSES API ─────────────────

@login_required
@csrf_exempt
@require_http_methods(["GET", "POST"])
def expenses_list(request):

    if request.method == "GET":
        if request.user.is_staff:
            expenses = Expense.objects.all()
        else:
            expenses = Expense.objects.filter(user=request.user)

        data = list(expenses.values(
            'id', 'date', 'time', 'amount', 'category',
            'where_spent', 'payment_method', 'title', 'notes'
        ))

        for e in data:
            e['date'] = str(e['date'])
            e['amount'] = float(e['amount'])
            e['time'] = str(e['time'])[:5] if e['time'] else None

        return JsonResponse(data, safe=False)

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

            where_spent = (data.get("whereSpent") or "").strip().title()
            if not where_spent:
                return JsonResponse({"error": "Where spent is required"}, status=400)

            date_str = data.get("date")
            if not date_str:
                return JsonResponse({"error": "Date is required"}, status=400)

            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"error": "Invalid date format"}, status=400)

            if parsed_date > date_type.today():
                return JsonResponse({"error": "Date cannot be in the future"}, status=400)

            expense = Expense.objects.create(
                user=request.user,
                title=(data.get("title") or "").strip(),
                amount=amount,
                category=category,
                payment_method=payment_method,
                where_spent=where_spent,
                date=date_str,
                time=data.get("time") or None,
                notes=(data.get("notes") or "").strip(),
            )

            return JsonResponse({"message": "Expense added", "id": expense.id}, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


# ───────────────── EXPENSE DETAIL ─────────────────

@login_required
@csrf_exempt
@require_http_methods(["DELETE", "PUT"])
def expense_detail(request, id):

    try:
        if request.user.is_staff:
            expense = Expense.objects.get(id=id)
        else:
            expense = Expense.objects.get(id=id, user=request.user)
    except Expense.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "DELETE":
        expense.delete()
        return JsonResponse({"message": "Deleted"})

    elif request.method == "PUT":
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

            where_spent = (data.get("whereSpent") or "").strip().title()
            if not where_spent:
                return JsonResponse({"error": "Where spent is required"}, status=400)

            date_str = data.get("date")
            if not date_str:
                return JsonResponse({"error": "Date is required"}, status=400)

            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"error": "Invalid date format"}, status=400)

            if parsed_date > date_type.today():
                return JsonResponse({"error": "Date cannot be in the future"}, status=400)

            expense.title = (data.get("title") or "").strip()
            expense.amount = amount
            expense.category = category
            expense.payment_method = payment_method
            expense.where_spent = where_spent
            expense.date = date_str
            expense.time = data.get("time") or None
            expense.notes = (data.get("notes") or "").strip()
            expense.save()

            return JsonResponse({"message": "Expense updated", "id": expense.id})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


# ───────────────── INSIGHTS ─────────────────

@login_required
def insights(request):
    if request.user.is_staff:
        expenses = Expense.objects.all()
    else:
        expenses = Expense.objects.filter(user=request.user)
    data = generate_insights(expenses)
    return JsonResponse(data)


# ───────────────── CLEAR ALL ─────────────────

@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def clear_all_expenses(request):
    Expense.objects.filter(user=request.user).delete()
    return JsonResponse({"message": "All expenses cleared"})