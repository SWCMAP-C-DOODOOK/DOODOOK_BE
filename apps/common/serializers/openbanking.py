# moved from apps/common/serializers.py
from rest_framework import serializers

from apps.common.models import OpenBankingAccount


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
    fintech_use_num = serializers.CharField(max_length=24)

    def validate_fintech_use_num(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("fintech_use_num is required")
        return value


class OpenBankingTransactionQuerySerializer(serializers.Serializer):
    fintech_use_num = serializers.CharField(max_length=24)
    from_date = serializers.CharField()
    to_date = serializers.CharField()
    sort = serializers.CharField(required=False, default="time")
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    size = serializers.IntegerField(required=False, min_value=1, max_value=500, default=100)

    def validate(self, attrs):
        from_date = attrs.get("from_date")
        to_date = attrs.get("to_date")
        for field_name, value in ("from_date", from_date), ("to_date", to_date):
            if value is None:
                raise serializers.ValidationError({field_name: "This field is required."})
            if len(value) != 8 or not value.isdigit():
                raise serializers.ValidationError({field_name: "Use YYYYMMDD format."})
        if from_date > to_date:
            raise serializers.ValidationError({"range": "from_date cannot be greater than to_date."})
        if not attrs.get("fintech_use_num"):
            raise serializers.ValidationError({"fintech_use_num": "fintech_use_num is required"})
        return attrs
