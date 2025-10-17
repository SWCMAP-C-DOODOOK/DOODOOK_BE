# moved from apps/common/models.py
from django.conf import settings
from django.db import models

from apps.groups.models import Group, GroupMembership

from . import TimeStampedModel


class Payment(TimeStampedModel):
    """Monthly dues payment record."""

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="payments",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    membership = models.ForeignKey(
        GroupMembership,
        on_delete=models.CASCADE,
        related_name="payments",
        null=True,
        blank=True,
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
                fields=["group", "user", "year", "month"],
                name="unique_group_user_year_month_payment",
            ),
        ]
        indexes = [
            models.Index(
                fields=["group", "user", "year", "month"],
                name="idx_pay_group_user_ym",
            ),
        ]
        ordering = ["-year", "-month", "user"]

    # TODO: sprint5에서 자동 납부 연동 필드 추가 예정
