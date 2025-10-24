# policies/admin.py

from django.contrib import admin
from .models import Policy

@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    # (생략)
    list_display = ('policy_type', 'title', 'version', 'is_active', 'effective_date', 'updated_at')
    # (생략)
    list_editable = ('is_active',)