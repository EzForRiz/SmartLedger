# backend/apps/rosca/services.py

import random

from django.utils import timezone

from .models import DrawWinner, PaymentRecord, Participant, ROSCAGroup


class DrawError(Exception):
    """Raised when a monthly draw cannot be completed."""


def get_latest_winner():
    """Return the most recent draw winner across all groups, or None."""
    return (
        DrawWinner.objects.select_related("participant", "group")
        .order_by("-year", "-month", "-drawn_at")
        .first()
    )


def get_current_period():
    today = timezone.localdate()
    return today.month, today.year


def run_monthly_draw(group, month=None, year=None):
    """
    Select a random eligible winner for the given ROSCA group and month.

    Eligibility:
      1. Successful payment for the target month/year.
      2. Has not won any previous draw in this group's current cycle.
    """
    if month is None or year is None:
        month, year = get_current_period()

    if DrawWinner.objects.filter(group=group, month=month, year=year).exists():
        raise DrawError(f"A draw for {group.name} has already been held for {month}/{year}.")

    paid_participant_ids = PaymentRecord.objects.filter(
        participant__group=group,
        month=month,
        year=year,
        status=PaymentRecord.STATUS_SUCCESS,
    ).values_list("participant_id", flat=True)

    previous_winner_ids = DrawWinner.objects.filter(
        group=group,
    ).values_list("participant_id", flat=True)

    eligible = Participant.objects.filter(
        id__in=paid_participant_ids,
    ).exclude(
        id__in=previous_winner_ids,
    )

    eligible_list = list(eligible)
    if not eligible_list:
        raise DrawError(
            "No eligible participants found. Everyone may have already won, "
            "or no successful payments exist for this month."
        )

    winner = random.choice(eligible_list)

    return DrawWinner.objects.create(
        group=group,
        participant=winner,
        month=month,
        year=year,
        prize_amount=group.total_payout,
    )


def get_participant_for_user(user):
    """Most recent participation for the logged-in user."""
    return (
        Participant.objects.select_related("group")
        .filter(user=user)
        .order_by("-joined_at")
        .first()
    )


def create_deposit(participant, month=None, year=None):
    """
    Simulate a monthly deposit for a participant.
    Raises ValueError if already paid for the period.
    """
    if month is None or year is None:
        month, year = get_current_period()

    if participant.has_paid_for(month, year):
        raise ValueError(f"You have already paid for {month}/{year}.")

    return PaymentRecord.objects.create(
        participant=participant,
        month=month,
        year=year,
        amount=participant.group.monthly_contribution,
        status=PaymentRecord.STATUS_SUCCESS,
    )
