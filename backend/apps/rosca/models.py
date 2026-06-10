# backend/apps/rosca/models.py

import uuid

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, RegexValidator, MaxValueValidator
from django.core.exceptions import ValidationError


CNIC_VALIDATOR = RegexValidator(
    regex=r"^[0-9]{5}-[0-9]{7}-[0-9]{1}$",
    message="CNIC must be exactly 13 digits.",
)

PHONE_VALIDATOR = RegexValidator(
    regex=r"^03[0-9]{9}$",
    message="Phone number must be 11 digits starting with 03 (e.g. 03001234567).",
)


class ROSCAGroup(models.Model):
    """A rotating savings pool / committee."""

    name = models.CharField(max_length=120)
    total_payout = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(1)],
        help_text="Total prize pool paid to the monthly winner.",
    )
    monthly_contribution = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(1)],
        help_text="Fixed amount each member pays every month.",
    )
    duration_months = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        help_text="Total cycle length in months.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_active", "name"]
        verbose_name = "ROSCA Group"
        verbose_name_plural = "ROSCA Groups"

    def __str__(self):
        status = "Active" if self.is_active else "Closed"
        return f"{self.name} ({status})"

    @property
    def member_count(self):
        return self.participants.count()


class Participant(models.Model):
    """Links a user to a ROSCA group with KYC details."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="rosca_participations",
    )
    group = models.ForeignKey(
        ROSCAGroup,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=15, validators=[PHONE_VALIDATOR])
    cnic = models.CharField(max_length=15, validators=[CNIC_VALIDATOR])
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-joined_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "group"],
                name="unique_user_per_rosca_group",
            ),
            models.UniqueConstraint(
                fields=["group", "cnic"],
                name="unique_cnic_per_rosca_group",
            ),
        ]

    def __str__(self):
        return f"{self.full_name} — {self.group.name}"

    def months_paid_count(self):
        return self.payments.filter(status=PaymentRecord.STATUS_SUCCESS).count()

    def has_paid_for(self, month, year):
        return self.payments.filter(
            month=month,
            year=year,
            status=PaymentRecord.STATUS_SUCCESS,
        ).exists()

    def has_won_in_cycle(self):
        return self.draw_wins.filter(group=self.group).exists()


class PaymentRecord(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    year = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    transaction_id = models.CharField(max_length=32, unique=True, editable=False)
    paid_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "-month", "-paid_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["participant", "month", "year"],
                name="unique_payment_per_participant_month",
            ),
        ]

    def __str__(self):
        return f"{self.transaction_id} — {self.participant.full_name} ({self.month}/{self.year})"

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = self._generate_transaction_id()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_transaction_id():
        return f"SL-{uuid.uuid4().hex[:12].upper()}"


class DrawWinner(models.Model):
    """Records the monthly lucky-draw winner for a ROSCA group."""

    group = models.ForeignKey(
        ROSCAGroup,
        on_delete=models.CASCADE,
        related_name="draw_winners",
    )
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="draw_wins",
    )
    month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    year = models.PositiveIntegerField()
    prize_amount = models.DecimalField(max_digits=12, decimal_places=2)
    drawn_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "-month", "-drawn_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "month", "year"],
                name="unique_draw_per_group_month",
            ),
        ]

    def __str__(self):
        return f"{self.participant.full_name} won {self.group.name} ({self.month}/{self.year})"

    def clean(self):
        if self.participant_id and self.group_id:
            if self.participant.group_id != self.group_id:
                raise ValidationError("Winner must belong to the selected ROSCA group.")
