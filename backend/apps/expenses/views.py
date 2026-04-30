# apps/expenses/views.py

import json
from datetime import datetime, date as date_type
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import Expense
from apps.ai_insights.services import generate_insights


# Helpers

def parse_date(date_str):
    if "/" in date_str:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def parse_time(time_str):
    if not time_str:
        return None
    return datetime.strptime(time_str, "%H:%M").time()


def validate_common(data):
    amount = float(data.get("amount", 0))
    if amount <= 0:
        return None, "Amount must be positive"
    if amount > 9999999:
        return None, "Amount too large"

    category = data.get("category")
    if category not in ("Personal", "Professional"):
        return None, "Invalid category"

    payment = data.get("paymentMethod")
    if payment not in ("cash", "card", "easypaisa", "jazzcash"):
        return None, "Invalid payment method"

    where_spent = (data.get("whereSpent") or "").strip().title()
    if not where_spent:
        return None, "Where spent required"

    date_str = data.get("date")
    if not date_str:
        return None, "Date required"

    parsed_date = parse_date(date_str)

    if parsed_date > timezone.localdate():
        return None, "Future dates not allowed"

    return {
        "amount": amount,
        "category": category,
        "payment": payment,
        "where_spent": where_spent,
        "date": parsed_date
    }, None


# Authentication

def login_view(request):
    if request.user.is_authenticated:
        return redirect('/')

    error = None
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", "")
        )
        if user:
            login(request, user)
            return redirect('/')
        error = "Invalid username or password"

    return render(request, "login.html", {"error": error})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('/')

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm_password", "")

        if not username or not password:
            error = "All fields required"
        elif len(password) < 6:
            error = "Password too short"
        elif password != confirm:
            error = "Passwords do not match"
        elif User.objects.filter(username=username).exists():
            error = "Username already exists"
        else:
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            return redirect('/')

    return render(request, "register.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("/login/")


#  PAGES 

@login_required
def home(request):
    return render(request, "index.html")


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


@login_required
def rosca(request):
    return render(request, "rosca.html")


#  EXPENSES API 

@login_required
@csrf_exempt
@require_http_methods(["GET", "POST"])
def expenses_list(request):

    # GET
    if request.method == "GET":
        qs = Expense.objects.all() if request.user.is_staff else Expense.objects.filter(user=request.user)

        data = list(qs.values(
            "id", "date", "time", "amount", "category",
            "where_spent", "payment_method", "title", "notes"
        ))

        for e in data:
            e["date"] = str(e["date"])
            e["time"] = str(e["time"])[:5] if e["time"] else None
            e["amount"] = float(e["amount"])

        return JsonResponse({"success": True, "data": data})

    # POST
    try:
        data = json.loads(request.body)

        validated, error = validate_common(data)
        if error:
            return JsonResponse({"success": False, "error": error}, status=400)

        expense = Expense.objects.create(
            user=request.user,
            title=(data.get("title") or "").strip(),
            amount=validated["amount"],
            category=validated["category"],
            payment_method=validated["payment"],
            where_spent=validated["where_spent"],
            date=validated["date"],
            time=parse_time(data.get("time")),
            notes=(data.get("notes") or "").strip(),
        )

        return JsonResponse({"success": True, "id": expense.id}, status=201)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


# DETAIL

@login_required
@csrf_exempt
@require_http_methods(["PUT", "DELETE"])
def expense_detail(request, id):

    try:
        expense = Expense.objects.get(id=id, user=request.user)
    except Expense.DoesNotExist:
        return JsonResponse({"success": False, "error": "Not found"}, status=404)

    if request.method == "DELETE":
        expense.delete()
        return JsonResponse({"success": True})

    try:
        data = json.loads(request.body)

        validated, error = validate_common(data)
        if error:
            return JsonResponse({"success": False, "error": error}, status=400)

        expense.title = (data.get("title") or "").strip()
        expense.amount = validated["amount"]
        expense.category = validated["category"]
        expense.payment_method = validated["payment"]
        expense.where_spent = validated["where_spent"]
        expense.date = validated["date"]
        expense.time = parse_time(data.get("time"))
        expense.notes = (data.get("notes") or "").strip()
        expense.save()

        return JsonResponse({"success": True, "id": expense.id})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


# INSIGHTS 

@login_required
def insights(request):
    qs = Expense.objects.all() if request.user.is_staff else Expense.objects.filter(user=request.user)
    return JsonResponse({
        "success": True,
        "data": generate_insights(qs)
    })


# CLEAR ALL

@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def clear_all_expenses(request):
    Expense.objects.filter(user=request.user).delete()
    return JsonResponse({"success": True})