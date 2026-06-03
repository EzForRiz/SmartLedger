# apps/expenses/views.py

import json
from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import Expense, IncomeHistory
from .services import get_monthly_finance, get_income_for_month
from apps.ai_insights.services import generate_insights


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def parse_date(date_str):
    if not date_str:
        return None
    try:
        if "/" in date_str:
            return datetime.strptime(date_str, "%d/%m/%Y").date()
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None


def parse_time(time_str):
    if not time_str:
        return None
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except Exception:
        return None


def validate_common(data):
    try:
        amount = float(data.get("amount", 0))
    except (TypeError, ValueError):
        return None, "Amount must be a number"

    if amount <= 0:
        return None, "Amount must be positive"

    category = data.get("category")
    if category not in ("Personal", "Professional"):
        return None, "Invalid category"

    payment = data.get("paymentMethod")
    if payment not in ("cash", "card", "easypaisa", "jazzcash"):
        return None, "Invalid payment method"

    where_spent = (data.get("whereSpent") or "").strip()
    if not where_spent:
        return None, "Where spent is required"

    date = parse_date(data.get("date"))
    if not date:
        return None, "Invalid date"

    if date > timezone.localdate():
        return None, "Future dates not allowed"

    return {
        "amount": amount,
        "category": category,
        "payment": payment,
        "where_spent": where_spent,
        "date": date,
    }, None


def validate_income(data):
    try:
        amount = float(data.get("amount", 0))
    except (TypeError, ValueError):
        return None, "Invalid amount"

    if amount <= 0:
        return None, "Amount must be positive"

    effective_from = parse_date(data.get("effective_from"))
    if not effective_from:
        return None, "Invalid date"

    if effective_from > timezone.localdate():
        return None, "Future dates not allowed"

    return {
        "amount": amount,
        "effective_from": effective_from,
    }, None


# ─────────────────────────────────────────────
# PAGE VIEWS
# ─────────────────────────────────────────────

@login_required
def dashboard(request):
    from apps.rosca.services import get_latest_winner

    winner = get_latest_winner()
    return render(request, "dashboard.html", {"latest_winner": winner})


@login_required
def home(request):
    return render(request, "index.html")


# ─────────────────────────────────────────────
# EXPENSES API
# ─────────────────────────────────────────────

@login_required
@csrf_exempt
@require_http_methods(["GET", "POST"])
def expenses_list(request):

    if request.method == "GET":
        qs = Expense.objects.filter(user=request.user)
        data = list(qs.values(
            "id", "date", "time", "amount", "category",
            "where_spent", "payment_method", "title", "notes"
        ))
        for e in data:
            e["date"] = str(e["date"])
            e["amount"] = float(e["amount"])
            e["time"] = str(e["time"])[:5] if e["time"] else None

        return JsonResponse({"success": True, "data": data})

    data = json.loads(request.body)
    validated, error = validate_common(data)
    if error:
        return JsonResponse({"success": False, "error": error}, status=400)

    expense = Expense.objects.create(
        user=request.user,
        title=data.get("title", ""),
        amount=validated["amount"],
        category=validated["category"],
        payment_method=validated["payment"],
        where_spent=validated["where_spent"],
        date=validated["date"],
        time=parse_time(data.get("time")),
        notes=data.get("notes", ""),
    )

    return JsonResponse({"success": True, "id": expense.id}, status=201)


@login_required
@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def expense_detail(request, id):
    try:
        expense = Expense.objects.get(id=id, user=request.user)
    except Expense.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "GET":
        return JsonResponse({
            "id": expense.id,
            "amount": float(expense.amount),
            "category": expense.category,
            "date": str(expense.date),
            "payment_method": expense.payment_method,
            "where_spent": expense.where_spent,
            "title": expense.title,
            "notes": expense.notes,
        })

    if request.method == "DELETE":
        expense.delete()
        return JsonResponse({"success": True})

    if request.method == "PUT":
        data = json.loads(request.body)
        validated, error = validate_common(data)
        if error:
            return JsonResponse({"error": error}, status=400)

        expense.amount = validated["amount"]
        expense.category = validated["category"]
        expense.payment_method = validated["payment"]
        expense.where_spent = validated["where_spent"]
        expense.date = validated["date"]
        expense.time = parse_time(data.get("time"))
        expense.title = data.get("title", "")
        expense.notes = data.get("notes", "")
        expense.save()

        return JsonResponse({"success": True})


# ─────────────────────────────────────────────
# INCOME API
# ─────────────────────────────────────────────

@login_required
@csrf_exempt
@require_http_methods(["GET", "POST"])
def income_view(request):

    if request.method == "GET":
        today = timezone.localdate()
        total = get_income_for_month(request.user, today)
        return JsonResponse({
            "success": True,
            "data": {"monthly_total": total} if total > 0 else None,
        })

    data = json.loads(request.body)
    validated, error = validate_income(data)
    if error:
        return JsonResponse({"success": False, "error": error}, status=400)

    income = IncomeHistory.objects.create(
        user=request.user,
        amount=validated["amount"],
        effective_from=validated["effective_from"],
    )

    return JsonResponse({"success": True, "id": income.id}, status=201)


@login_required
@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def income_detail(request, id):
    try:
        income = IncomeHistory.objects.get(id=id, user=request.user)
    except IncomeHistory.DoesNotExist:
        return JsonResponse({"success": False, "error": "Not found"}, status=404)

    if request.method == "GET":
        return JsonResponse({
            "success": True,
            "data": {
                "id": income.id,
                "amount": float(income.amount),
                "effective_from": str(income.effective_from),
            },
        })

    if request.method == "DELETE":
        income.delete()
        return JsonResponse({"success": True})

    if request.method == "PUT":
        data = json.loads(request.body)
        validated, error = validate_income(data)
        if error:
            return JsonResponse({"success": False, "error": error}, status=400)

        income.amount = validated["amount"]
        income.effective_from = validated["effective_from"]
        income.save()

        return JsonResponse({"success": True})


# ─────────────────────────────────────────────
# FINANCE SUMMARY
# ─────────────────────────────────────────────

@login_required
def finance_summary(request):
    today = timezone.localdate()
    data = get_monthly_finance(request.user, today)
    return JsonResponse({"success": True, "data": data})


# ─────────────────────────────────────────────
# INSIGHTS  — now passes income to the AI
# ─────────────────────────────────────────────

@login_required
def insights(request):
    qs = Expense.objects.filter(user=request.user)

    # Get user's current monthly income so the AI can use it
    today = timezone.localdate()
    income = get_income_for_month(request.user, today)   # returns 0.0 if not set

    return JsonResponse({
        "success": True,
        "data": generate_insights(qs, income=income),
    })


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    error = None
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password"),
        )
        if user:
            login(request, user)
            return redirect("/")
        error = "Invalid credentials"

    return render(request, "login.html", {"error": error})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm_password", "")

        if len(password) < 6:
            error = "Password must be at least 6 characters"
        elif password != confirm:
            error = "Passwords do not match"
        elif User.objects.filter(username=username).exists():
            error = "Username already taken"
        else:
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            return redirect("/")

    return render(request, "register.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("/login/")


# ─────────────────────────────────────────────
# CLEAR ALL EXPENSES
# ─────────────────────────────────────────────

@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def clear_all_expenses(request):
    Expense.objects.filter(user=request.user).delete()
    return JsonResponse({"success": True})



@login_required
@require_http_methods(["GET"])
def income_history_view(request):
    """
    Returns all IncomeHistory records for the logged-in user,
    ordered newest-effective-date first.
    """
    records = IncomeHistory.objects.filter(user=request.user).order_by("-effective_from")
    data = [
        {
            "id":             r.id,
            "amount":         float(r.amount),
            "effective_from": str(r.effective_from),
            "created_at":     r.created_at.isoformat(),
        }
        for r in records
    ]
    return JsonResponse({"success": True, "data": data})
 