# migration 필요
from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.groups.models import Group, GroupMembership


class DuesReminder(TimeStampedModel):
    class Channel(models.TextChoices):
        APP = "app", "app"
        EMAIL = "email", "email"
        SMS = "sms", "sms"

    class Status(models.TextChoices):
        PENDING = "pending", "pending"
        SENT = "sent", "sent"
        FAILED = "failed", "failed"

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="dues_reminders",
        null=True,
        blank=True,
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dues_reminders",
    )
    target_membership = models.ForeignKey(
        GroupMembership,
        on_delete=models.CASCADE,
        related_name="dues_reminders",
        null=True,
        blank=True,
    )
    channel = models.CharField(max_length=16, choices=Channel.choices)
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    payload_json = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="dues_reminders_created",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-scheduled_at", "-created_at"]
