from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.common.serializers import PaymentSerializer  # noqa: F401
from apps.dues.models import DuesReminder
from apps.groups.models import GroupMembership


class DuesReminderSerializer(serializers.ModelSerializer):
    group_id = serializers.IntegerField(read_only=True)
    target_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all()
    )
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = DuesReminder
        fields = [
            "id",
            "group_id",
            "target_user",
            "channel",
            "scheduled_at",
            "sent_at",
            "status",
            "payload_json",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "sent_at",
            "status",
            "created_by",
            "created_at",
            "updated_at",
            "group_id",
        ]

    def validate(self, attrs):
        group = self.context.get("group")
        target_user = attrs.get("target_user")
        if group is not None and target_user is not None:
            membership = target_user.group_memberships.filter(
                group=group, status=GroupMembership.Status.ACTIVE
            ).first()
            if membership is None:
                raise serializers.ValidationError(
                    {"target_user": "Target user is not an active member of the group"}
                )
            attrs["target_membership"] = membership
        return super().validate(attrs)


class DuesReminderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DuesReminder
        fields = ["scheduled_at", "payload_json"]


__all__ = [
    "PaymentSerializer",
    "DuesReminderSerializer",
    "DuesReminderUpdateSerializer",
]
