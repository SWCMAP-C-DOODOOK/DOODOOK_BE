# moved from apps/common/models/budget.py
from django.db import models

from apps.common.models.base import TimeStampedModel


class Budget(TimeStampedModel):
    """Budget allocation per category."""

    name = models.CharField(max_length=50)
    allocated_amount = models.PositiveIntegerField()
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.name} / {self.allocated_amount:,}원"