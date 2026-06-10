# backend/apps/rosca/views.py

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import ROSCARegistrationForm
from .models import PaymentRecord, ROSCAGroup
from .services import (
    DrawError,
    create_deposit,
    get_current_period,
    get_latest_winner,
    get_participant_for_user,
    run_monthly_draw,
)


def _winner_context():
    winner = get_latest_winner()
    if not winner:
        return {"latest_winner": None}
    return {
        "latest_winner": winner,
        "winner_name": winner.participant.full_name,
        "winner_prize": winner.prize_amount,
        "winner_month": winner.month,
        "winner_year": winner.year,
        "winner_group": winner.group.name,
    }


@login_required
def rosca_index(request):
    participant = get_participant_for_user(request.user)
    context = {
        "participant": participant,
        "active_pools": ROSCAGroup.objects.filter(is_active=True),
        **_winner_context(),
    }
    return render(request, "rosca/index.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def rosca_register(request):
    existing = get_participant_for_user(request.user)
    if existing and request.method == "GET":
        return redirect("rosca_account")

    if request.method == "POST":
        form = ROSCARegistrationForm(request.POST, user=request.user)
        if form.is_valid():
            participant = form.save()
            messages.success(
                request,
                f"Welcome to {participant.group.name}! You can now make your monthly deposit.",
            )
            return redirect("rosca_account")
    else:
        form = ROSCARegistrationForm(user=request.user)

    return render(request, "rosca/register.html", {"form": form})


@login_required
def rosca_account(request):
    participant = get_participant_for_user(request.user)
    if not participant:
        messages.info(request, "Join a ROSCA pool to access your committee account.")
        return redirect("rosca_register")

    month, year = get_current_period()
    payments = participant.payments.filter(status=PaymentRecord.STATUS_SUCCESS)
    months_paid = payments.count()
    current_paid = participant.has_paid_for(month, year)
    has_won = participant.has_won_in_cycle()

    context = {
        "participant": participant,
        "months_paid": months_paid,
        "total_months": participant.group.duration_months,
        "current_month": month,
        "current_year": year,
        "current_paid": current_paid,
        "pending_amount": participant.group.monthly_contribution,
        "has_won": has_won,
        "payment_history": payments[:12],
        **_winner_context(),
    }
    return render(request, "rosca/account.html", context)


@login_required
@require_http_methods(["POST"])
def rosca_deposit(request):
    participant = get_participant_for_user(request.user)
    if not participant:
        messages.error(request, "You must register for a ROSCA pool first.")
        return redirect("rosca_register")

    try:
        payment = create_deposit(participant)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("rosca_account")

    messages.success(request, "Deposit recorded successfully!")
    return redirect("rosca_receipt", payment_id=payment.id)


@login_required
def rosca_receipt(request, payment_id):
    payment = get_object_or_404(
        PaymentRecord.objects.select_related("participant", "participant__group"),
        id=payment_id,
        participant__user=request.user,
        status=PaymentRecord.STATUS_SUCCESS,
    )
    return render(request, "rosca/receipt.html", {"payment": payment})


@staff_member_required
@require_http_methods(["GET", "POST"])
def rosca_admin_draw(request):
    groups = ROSCAGroup.objects.filter(is_active=True)
    month, year = get_current_period()
    result = None
    error = None

    if request.method == "POST":
        group_id = request.POST.get("group_id")
        group = get_object_or_404(ROSCAGroup, id=group_id, is_active=True)
        try:
            result = run_monthly_draw(group, month, year)
            messages.success(
                request,
                f"Draw complete! {result.participant.full_name} won Rs. {result.prize_amount:,.0f}.",
            )
        except DrawError as exc:
            error = str(exc)
            messages.error(request, error)

    context = {
        "groups": groups,
        "current_month": month,
        "current_year": year,
        "result": result,
        "error": error,
        "recent_winners": get_latest_winner(),
        **_winner_context(),
    }
    return render(request, "rosca/admin_draw.html", context)
