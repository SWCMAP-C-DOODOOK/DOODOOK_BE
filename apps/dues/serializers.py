from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.common.serializers import PaymentSerializer  # noqa: F401
from apps.dues.models import DuesReminder


class DuesReminderSerializer(serializers.ModelSerializer):
    target_user = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = DuesReminder
        fields = [
            "id",
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
        read_only_fields = ["sent_at", "status", "created_by", "created_at", "updated_at"]


class DuesReminderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DuesReminder
        fields = ["scheduled_at", "payload_json"]


__all__ = ["PaymentSerializer", "DuesReminderSerializer", "DuesReminderUpdateSerializer"]
