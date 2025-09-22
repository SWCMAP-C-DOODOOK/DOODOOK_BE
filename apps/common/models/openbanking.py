# moved from apps/common/models.py
from django.db import models

from . import TimeStampedModel


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
