from django.contrib import admin

from .models import DrawWinner, Participant, PaymentRecord, ROSCAGroup


@admin.register(ROSCAGroup)
class ROSCAGroupAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "monthly_contribution",
        "total_payout",
        "duration_months",
        "member_count",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "group",
        "phone_number",
        "cnic",
        "months_paid_count",
        "joined_at",
    )

    list_filter = (
        "group",
    )

    search_fields = (
        "full_name",
        "cnic",
        "user__username",
    )

    autocomplete_fields = (
        "user",
        "group",
    )

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

    list_filter = (
        "status",
        "month",
        "year",
        "participant__group",
    )

    search_fields = (
        "transaction_id",
        "participant__full_name",
    )

    readonly_fields = (
        "transaction_id",
        "paid_at",
    )

    autocomplete_fields = (
        "participant",
    )


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

    list_filter = (
        "group",
        "year",
        "month",
    )

    search_fields = (
        "participant__full_name",
    )

    autocomplete_fields = (
        "participant",
        "group",
    )

    readonly_fields = (
        "drawn_at",
    )


admin.site.site_header = "SmartLedger Admin"
admin.site.site_title = "SmartLedger"
admin.site.index_title = "ROSCA Committee Administration"