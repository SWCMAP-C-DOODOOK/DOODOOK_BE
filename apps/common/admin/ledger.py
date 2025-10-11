# moved from apps/common/admin.py
from django.contrib import admin

from apps.common.models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "budget",
        "type",
        "amount",
        "date",
        "category",
        "created_at",
    )
    list_filter = ("type", "date", "category", "budget")
    search_fields = (
        "description",
        "category",
        "user__username",
        "user__email",
        "budget__name",
    )
    ordering = ("-date", "-id")
