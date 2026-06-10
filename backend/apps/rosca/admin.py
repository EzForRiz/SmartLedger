# backend/apps/rosca/admin.py

from django.contrib import admin

from .models import DrawWinner, Participant, PaymentRecord, ROSCAGroup


@admin.register(ROSCAGroup)
class ROSCAGroupAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "monthly_contribution",
        "total_payout",
        "duration_months",
        "is_active",
        "member_count",
    )
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("full_name", "group", "user", "phone_number", "cnic", "joined_at")
    list_filter = ("group",)
    search_fields = ("full_name", "cnic", "user__username")


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id",
        "participant",
        "month",
        "year",
        "amount",
        "status",
        "paid_at",
    )
    list_filter = ("status", "year", "month", "participant__group")
    search_fields = ("transaction_id", "participant__full_name")
    readonly_fields = ("transaction_id", "paid_at")


@admin.register(DrawWinner)
class DrawWinnerAdmin(admin.ModelAdmin):
    list_display = (
        "participant",
        "group",
        "month",
        "year",
        "prize_amount",
        "drawn_at",
    )
    list_filter = ("group", "year", "month")
    search_fields = ("participant__full_name",)
