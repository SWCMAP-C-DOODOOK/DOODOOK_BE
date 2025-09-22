# moved from apps/common/models.py
from django.conf import settings
from django.db import models

from . import TimeStampedModel


class Transaction(TimeStampedModel):
    """Household ledger transaction."""

    class TransactionType(models.TextChoices):
        INCOME = "income", "income"
        EXPENSE = "expense", "expense"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    budget = models.ForeignKey('common.Budget', on_delete=models.SET_NULL, related_name="transactions", blank=True, null=True)
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
            models.Index(fields=["date"], name="idx_transaction_date"),
            models.Index(fields=["type", "date"], name="idx_transaction_type_date"),
        ]
        ordering = ["-date", "-id"]

    # TODO: sprint7에서 다중 예산 배분(M2M) 확장 검토
    # TODO: sprint6에서 OCR 신뢰도 스코어 필드 추가 고려
