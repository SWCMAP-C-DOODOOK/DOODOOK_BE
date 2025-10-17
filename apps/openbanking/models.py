# moved from apps/common/models/openbanking.py
from django.db import models

from apps.common.models.base import TimeStampedModel
from apps.groups.models import Group


class OpenBankingAccount(TimeStampedModel):
    """Linked Fintech OpenBanking account metadata."""

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="openbanking_accounts",
        null=True,
        blank=True,
    )
    alias = models.CharField(max_length=50)
    fintech_use_num = models.CharField(max_length=24, db_index=True)
    bank_name = models.CharField(max_length=50, blank=True, null=True)
    account_masked = models.CharField(max_length=64, blank=True, null=True)
    enabled = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.alias}({self.fintech_use_num})"

    class Meta:
        unique_together = [("group", "fintech_use_num")]
        ordering = ["alias", "id"]
