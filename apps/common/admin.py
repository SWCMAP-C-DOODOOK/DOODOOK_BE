from django.contrib import admin
from django.db.models import Sum

from .models import Budget, OpenBankingAccount, Payment, Transaction


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "allocated_amount", "used_amount", "remaining_amount", "used_percent", "created_at", "updated_at")
    search_fields = ("name",)
    readonly_fields = ("used_amount", "remaining_amount", "used_percent")
    ordering = ("name",)

    def _usage(self, obj):
        cached = getattr(obj, "_cached_used_amount", None)
        if cached is not None:
            return cached
        direct = obj.transactions.filter(type=Transaction.TransactionType.EXPENSE).aggregate(total=Sum("amount")).get("total") or 0
        category = Transaction.objects.filter(
            budget__isnull=True,
            category=obj.name,
            type=Transaction.TransactionType.EXPENSE,
        ).aggregate(total=Sum("amount")).get("total") or 0
        obj._cached_used_amount = int(direct) + int(category)
        return obj._cached_used_amount

    def used_amount(self, obj):
        return self._usage(obj)

    def remaining_amount(self, obj):
        return obj.allocated_amount - self._usage(obj)

    def used_percent(self, obj):
        allocated = obj.allocated_amount or 0
        if not allocated:
            return 0.0
        return round((self._usage(obj) / allocated) * 100, 2)

    used_amount.short_description = "Used"
    remaining_amount.short_description = "Remaining"
    used_percent.short_description = "Used %"


@admin.register(OpenBankingAccount)
class OpenBankingAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "alias", "fintech_use_num", "bank_name", "enabled", "created_at")
    list_filter = ("enabled", "bank_name")
    search_fields = ("alias", "fintech_use_num", "bank_name")
    ordering = ("alias",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "year", "month", "is_paid", "amount", "paid_at", "created_at")
    list_filter = ("year", "month", "is_paid")
    search_fields = ("user__username", "user__email")
    ordering = ("-year", "-month", "user__username")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "budget", "type", "amount", "date", "category", "created_at")
    list_filter = ("type", "date", "category", "budget")
    search_fields = ("description", "category", "user__username", "user__email", "budget__name")
    ordering = ("-date", "-id")
