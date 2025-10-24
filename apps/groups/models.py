from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Group(TimeStampedModel):
    """Logical organization unit for accounting features."""

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    invite_code = models.CharField(
        max_length=16,
        unique=True,
        null=True,
        blank=True,
        help_text="6-character alphanumeric invite code",
    )
    invite_code_expires_at = models.DateTimeField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_groups",
    )

    class Meta:
        ordering = ["name", "id"]
        unique_together = [("owner", "name")]

    def __str__(self) -> str:
        return self.name


class GroupMembership(TimeStampedModel):
    """User membership and role association to a group."""

    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INVITED = "invited", "Invited"
        PENDING = "pending", "Pending"
        SUSPENDED = "suspended", "Suspended"
        LEFT = "left", "Left"

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="group_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.MEMBER,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="group_invitations_sent",
    )
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("group", "user")]
        ordering = ["group_id", "user_id"]

    def __str__(self) -> str:
        return f"{self.user_id} -> {self.group_id} ({self.role})"
