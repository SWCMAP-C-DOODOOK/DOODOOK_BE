from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import serializers

from apps.users.serializers import UserSerializer

from .models import Budget, OpenBankingAccount, Payment, Transaction


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


class TransactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    budget_id = serializers.PrimaryKeyRelatedField(source="budget", queryset=Budget.objects.all(), write_only=True, required=False, allow_null=True)
    budget = serializers.SerializerMethodField()
    receipt_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "user",
            "budget_id",
            "budget",
            "amount",
            "description",
            "date",
            "type",
            "category",
            "receipt_image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "budget", "created_at", "updated_at"]

    def validate_amount(self, value: int) -> int:
        if value is None or value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        return value

    def get_budget(self, obj):
        if obj.budget_id:
            budget = getattr(obj, "budget", None)
            if budget:
                return {"id": budget.id, "name": budget.name}
            return {"id": obj.budget_id, "name": None}
        return None


class ReceiptOCRRequestSerializer(serializers.Serializer):
    transaction_id = serializers.IntegerField(required=False, min_value=1)
    store = serializers.BooleanField(required=False, default=False)
    overwrite = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        has_image = self.context.get("has_image", False)
        transaction_id = attrs.get("transaction_id")
        store = attrs.get("store", False)

        if not transaction_id and not has_image:
            raise serializers.ValidationError("Provide transaction_id or upload image")

        if store and not transaction_id:
            raise serializers.ValidationError("transaction_id is required when store=true")

        return attrs


class BudgetSerializer(serializers.ModelSerializer):
    used = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()
    used_percent = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            "id",
            "name",
            "allocated_amount",
            "description",
            "used",
            "remaining",
            "used_percent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "used",
            "remaining",
            "used_percent",
            "created_at",
            "updated_at",
        ]

    def _usage(self, obj) -> int:
        usage_map = self.context.get("budget_usage", {}) or {}
        return int(usage_map.get(obj.id, 0) or 0)

    def get_used(self, obj) -> int:
        return self._usage(obj)

    def get_remaining(self, obj) -> int:
        return obj.allocated_amount - self._usage(obj)

    def get_used_percent(self, obj) -> float:
        allocated = obj.allocated_amount or 0
        if not allocated:
            return 0.0
        return round((self._usage(obj) / allocated) * 100, 2)


class BudgetWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ["name", "allocated_amount", "description"]

    def validate_allocated_amount(self, value: int) -> int:
        if value is None or value <= 0:
            raise serializers.ValidationError("allocated_amount must be greater than zero")
        return value

    def validate_name(self, value: str) -> str:
        qs = Budget.objects.filter(name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Budget name must be unique")
        return value


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
