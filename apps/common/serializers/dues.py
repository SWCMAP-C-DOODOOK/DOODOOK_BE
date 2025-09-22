# moved from apps/common/serializers.py
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import serializers

from apps.common.models import Payment


User = get_user_model()


class PaymentSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(source="user", queryset=User.objects.all())
    is_paid = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Payment
        fields = ["id", "user_id", "year", "month", "is_paid", "amount", "paid_at"]
        read_only_fields = ["paid_at"]

    def validate_year(self, value: int) -> int:
        if value <= 0:
            raise serializers.ValidationError("Year must be a positive integer")
        return value

    def validate_month(self, value: int) -> int:
        if value < 1 or value > 12:
            raise serializers.ValidationError("Month must be between 1 and 12")
        return value

    def create(self, validated_data):
        user = validated_data.pop("user")
        year = validated_data.pop("year")
        month = validated_data.pop("month")
        defaults = validated_data
        try:
            instance, created = Payment.objects.update_or_create(
                user=user,
                year=year,
                month=month,
                defaults=defaults,
            )
        except IntegrityError as exc:
            raise serializers.ValidationError({"non_field_errors": ["Payment entry already exists for the specified user/month."]}) from exc
        self.instance = instance
        self._created = created
        return instance

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError({"non_field_errors": ["Payment entry already exists for the specified user/month."]}) from exc


class DuesStatusSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    paid = serializers.BooleanField()
    amount = serializers.IntegerField(allow_null=True)
    paid_at = serializers.DateTimeField(allow_null=True)
