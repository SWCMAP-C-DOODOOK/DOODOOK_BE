# moved from apps/common/admin.py
from django.contrib import admin

from apps.common.models import OpenBankingAccount


@admin.register(OpenBankingAccount)
class OpenBankingAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "alias", "fintech_use_num", "bank_name", "enabled", "created_at")
    list_filter = ("enabled", "bank_name")
    search_fields = ("alias", "fintech_use_num", "bank_name")
    ordering = ("alias",)
