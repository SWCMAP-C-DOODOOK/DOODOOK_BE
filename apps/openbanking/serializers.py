# moved from apps/common/serializers/openbanking.py
from datetime import timedelta
from typing import Any, Dict

from rest_framework import serializers

from apps.openbanking.models import OpenBankingAccount


class OpenBankingAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenBankingAccount
        fields = [
            "id",
            "alias",
            "fintech_use_num",
            "bank_name",
            "account_masked",
            "enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OpenBankingBalanceQuerySerializer(serializers.Serializer):
    fintech_use_num = serializers.RegexField(
        regex=r"^[0-9A-Za-z]{4,24}$", max_length=24
    )

    def validate_fintech_use_num(self, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise serializers.ValidationError("fintech_use_num is required")
        return trimmed


class OpenBankingTransactionQuerySerializer(serializers.Serializer):
    fintech_use_num = serializers.RegexField(
        regex=r"^[0-9A-Za-z]{4,24}$", max_length=24
    )
    from_date = serializers.DateField(format="%Y-%m-%d", input_formats=["%Y-%m-%d"])
    to_date = serializers.DateField(format="%Y-%m-%d", input_formats=["%Y-%m-%d"])
    sort = serializers.ChoiceField(choices=["time", "amount"], default="time")
    page = serializers.IntegerField(
        required=False, min_value=1, max_value=1000, default=1
    )
    size = serializers.IntegerField(
        required=False, min_value=1, max_value=500, default=100
    )

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        fintech_use_num = attrs.get("fintech_use_num", "").strip()
        if not fintech_use_num:
            raise serializers.ValidationError(
                {"fintech_use_num": "fintech_use_num is required"}
            )

        from_date = attrs["from_date"]
        to_date = attrs["to_date"]
        if from_date > to_date:
            raise serializers.ValidationError(
                {"range": "from_date cannot be greater than to_date."}
            )
        if (to_date - from_date) > timedelta(days=93):
            raise serializers.ValidationError(
                {"range": "Maximum lookup window is 93 days."}
            )

        attrs["fintech_use_num"] = fintech_use_num
        attrs["from_date"] = from_date.strftime("%Y-%m-%d")
        attrs["to_date"] = to_date.strftime("%Y-%m-%d")
        return attrs


class OpenBankingAuthCallbackSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=128)
    scope = serializers.CharField(required=False, allow_blank=True, max_length=255)
    state = serializers.CharField(required=False, allow_blank=True, max_length=255)
