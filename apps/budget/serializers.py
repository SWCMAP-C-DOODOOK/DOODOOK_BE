# moved from apps/common/serializers/budget.py
from rest_framework import serializers

from apps.budget.models import Budget


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
