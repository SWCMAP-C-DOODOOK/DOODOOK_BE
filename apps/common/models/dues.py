# moved from apps/common/models.py
from django.conf import settings
from django.db import models

from . import TimeStampedModel


class Payment(TimeStampedModel):
    """Monthly dues payment record."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    is_paid = models.BooleanField(default=True)
    amount = models.PositiveIntegerField(blank=True, null=True)
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment(user={self.user_id}, date={self.year}-{self.month:02d}, paid={self.is_paid})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "year", "month"], name="unique_user_year_month_payment"
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "year", "month"], name="idx_payment_user_year_month"
            ),
        ]
        ordering = ["-year", "-month", "user"]

    # TODO: sprint5에서 자동 납부 연동 필드 추가 예정
