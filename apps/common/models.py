from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base with created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# migration 필요


class Payment(TimeStampedModel):
    """Monthly dues payment record."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    is_paid = models.BooleanField(default=True)
    amount = models.PositiveIntegerField(blank=True, null=True)
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment(user={self.user_id}, date={self.year}-{self.month:02d}, paid={self.is_paid})"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "year", "month"], name="unique_user_year_month_payment"),
        ]
        indexes = [
            models.Index(fields=["user", "year", "month"], name="idx_payment_user_year_month"),
        ]
        ordering = ["-year", "-month", "user"]

    # TODO: sprint5에서 자동 납부 연동 필드 추가 예정


class Budget(TimeStampedModel):
    """Budget allocation per category."""

    name = models.CharField(max_length=50)
    allocated_amount = models.PositiveIntegerField()
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.name} / {self.allocated_amount:,}원"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name"], name="uq_budget_name"),
        ]
        ordering = ["name"]


class OpenBankingAccount(TimeStampedModel):
    """Linked Fintech OpenBanking account metadata."""

    alias = models.CharField(max_length=50)
    fintech_use_num = models.CharField(max_length=24, unique=True, db_index=True)
    bank_name = models.CharField(max_length=50, blank=True, null=True)
    account_masked = models.CharField(max_length=64, blank=True, null=True)
    enabled = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.alias}({self.fintech_use_num})"

    class Meta:
        ordering = ["alias"]


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

# migration 필요
