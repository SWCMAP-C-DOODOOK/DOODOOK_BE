# moved from apps/common/models.py
from django.db import models

from . import TimeStampedModel


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
