# moved from apps/common/models.py
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base with created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


from .dues import Payment  # noqa: E402
from .budget import Budget  # noqa: E402
from .ledger import Transaction  # noqa: E402
from .openbanking import OpenBankingAccount  # noqa: E402

__all__ = [
    "TimeStampedModel",
    "Payment",
    "Budget",
    "Transaction",
    "OpenBankingAccount",
]
