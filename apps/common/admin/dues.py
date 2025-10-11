# moved from apps/common/admin.py
from django.contrib import admin

from apps.common.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "year",
        "month",
        "is_paid",
        "amount",
        "paid_at",
        "created_at",
    )
    list_filter = ("year", "month", "is_paid")
    search_fields = ("user__username", "user__email")
    ordering = ("-year", "-month", "user__username")
