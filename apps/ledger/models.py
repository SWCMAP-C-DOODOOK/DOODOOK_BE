# migration 필요
from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel, Transaction


class LedgerAuditLog(TimeStampedModel):
    class Action(models.TextChoices):
        CREATE = "create", "create"
        UPDATE = "update", "update"
        DELETE = "delete", "delete"

    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name="audit_logs")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ledger_audit_logs",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=16, choices=Action.choices)
    diff_json = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]
