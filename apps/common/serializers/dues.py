# moved from apps/common/serializers.py
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import serializers

from apps.common.models import Payment
from apps.groups.models import GroupMembership
from apps.groups.services import get_active_membership
from apps.users.serializers import GroupMembershipSerializer, UserSerializer

User = get_user_model()


class PaymentSerializer(serializers.ModelSerializer):
    group_id = serializers.IntegerField(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source="user", queryset=User.objects.all()
    )
    is_paid = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "group_id",
            "user_id",
            "membership",
            "year",
            "month",
            "is_paid",
            "amount",
            "paid_at",
        ]
        read_only_fields = ["group_id", "membership", "paid_at"]

    def validate_year(self, value: int) -> int:
        if value <= 0:
            raise serializers.ValidationError("Year must be a positive integer")
        return value

    def validate_month(self, value: int) -> int:
        if value < 1 or value > 12:
            raise serializers.ValidationError("Month must be between 1 and 12")
        return value

    def create(self, validated_data):
        group = validated_data.pop("group", None) or self.context.get("group")
        if group is None:
            raise serializers.ValidationError({"group_id": "Serializer context missing group"})
        user = validated_data.pop("user")
        membership = get_active_membership(group, user)
        if membership is None:
            raise serializers.ValidationError({"user_id": "User is not an active member of the group"})
        year = validated_data.pop("year")
        month = validated_data.pop("month")
        defaults = validated_data
        try:
            instance, created = Payment.objects.update_or_create(
                group=group,
                user=user,
                membership=membership,
                year=year,
                month=month,
                defaults=defaults,
            )
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "Payment entry already exists for the specified user/month."
                    ]
                }
            ) from exc
        self.instance = instance
        self._created = created
        return instance

    def update(self, instance, validated_data):
        group = validated_data.pop("group", None) or self.context.get("group")
        if group and instance.group_id not in (None, group.id):
            raise serializers.ValidationError({"group_id": "Payment belongs to a different group"})
        if group and instance.group_id is None:
            validated_data["group"] = group
        if group and "user" in validated_data:
            membership = get_active_membership(group, validated_data["user"])
            if membership is None:
                raise serializers.ValidationError({"user_id": "User is not an active member of the group"})
            validated_data["membership"] = membership
        try:
            return super().update(instance, validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "Payment entry already exists for the specified user/month."
                    ]
                }
            ) from exc

    def validate(self, attrs):
        group = self.context.get("group")
        user = attrs.get("user")
        if group and user:
            if not user.group_memberships.filter(
                group=group, status=GroupMembership.Status.ACTIVE
            ).exists():
                raise serializers.ValidationError(
                    {"user_id": "User is not an active member of the group"}
                )
        return super().validate(attrs)


class DuesStatusSerializer(serializers.Serializer):
    user = serializers.DictField()
    paid = serializers.BooleanField()
    amount = serializers.IntegerField(allow_null=True)
    paid_at = serializers.DateTimeField(allow_null=True)


class PaymentAdminSerializer(PaymentSerializer):
    user = UserSerializer(read_only=True)
    membership = GroupMembershipSerializer(read_only=True)

    class Meta(PaymentSerializer.Meta):
        fields = PaymentSerializer.Meta.fields + ["user", "membership"]
        read_only_fields = list(set(PaymentSerializer.Meta.read_only_fields + ["user", "membership"]))
