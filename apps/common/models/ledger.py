# moved from apps/common/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.groups.models import Group, GroupMembership

from . import TimeStampedModel


class Transaction(TimeStampedModel):
    """Household ledger transaction."""

    class TransactionType(models.TextChoices):
        INCOME = "income", "income"
        EXPENSE = "expense", "expense"

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="transactions",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions"
    )
    membership = models.ForeignKey(
        GroupMembership,
        on_delete=models.CASCADE,
        related_name="transactions",
        null=True,
        blank=True,
    )
    budget = models.ForeignKey(
        "budget.Budget",
        on_delete=models.SET_NULL,
        related_name="transactions",
        blank=True,
        null=True,
    )
    amount = models.PositiveIntegerField()
    description = models.CharField(max_length=255)
    date = models.DateField()
    type = models.CharField(max_length=10, choices=TransactionType.choices)
    category = models.CharField(max_length=50, blank=True, null=True)
    receipt_image = models.ImageField(upload_to="receipts/", blank=True, null=True)
    ocr_text = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        return f"[{self.type}] {self.date} {self.amount} {self.description}"

    class Meta:
        indexes = [
            models.Index(fields=["group", "date"], name="idx_tx_group_date"),
            models.Index(
                fields=["group", "type", "date"], name="idx_tx_group_type_date"
            ),
        ]
        ordering = ["-date", "-id"]

    # TODO: sprint7에서 다중 예산 배분(M2M) 확장 검토
    # TODO: sprint6에서 OCR 신뢰도 스코어 필드 추가 고려


# migration 필요
class OcrValidationLog(TimeStampedModel):
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="ocr_validation_logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ocr_validation_logs",
    )
    extracted_json = models.JSONField()
    is_valid = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


# migration 필요
class OcrApproval(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "pending"
        APPROVED = "approved", "approved"
        REJECTED = "rejected", "rejected"

    transaction = models.OneToOneField(
        Transaction, on_delete=models.CASCADE, related_name="ocr_approval"
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ocr_approvals",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    decided_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-updated_at"]

    def mark(self, *, reviewer, status: str, notes: str = ""):
        self.reviewer = reviewer
        self.status = status
        self.notes = notes
        self.decided_at = timezone.now()
        self.save(
            update_fields=["reviewer", "status", "notes", "decided_at", "updated_at"]
        )
