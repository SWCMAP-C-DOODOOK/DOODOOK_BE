# moved from apps/common/serializers.py
from rest_framework import serializers

from apps.common.models import Budget, Transaction
from apps.users.serializers import UserSerializer

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
