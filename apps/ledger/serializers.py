import os
import re
from typing import TYPE_CHECKING

from django.apps import apps
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

Budget = apps.get_model("budget", "Budget")
Transaction = apps.get_model("common", "Transaction")
try:  # optional models, guarded for projects without these apps
    Account = apps.get_model("account", "Account")
except LookupError:  # pragma: no cover
    Account = None
try:
    Category = apps.get_model("ledger", "Category")
except LookupError:  # pragma: no cover
    Category = None

from apps.users.serializers import UserSerializer

if TYPE_CHECKING:  # pragma: no cover
    from apps.budget.models import Budget  # noqa: F401


class TransactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    budget_id = serializers.PrimaryKeyRelatedField(
        source="budget",
        queryset=Budget.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
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

    def validate_date(self, value):
        if value is None:
            raise serializers.ValidationError("Date is required")
        if value > timezone.localdate():
            raise serializers.ValidationError("Date cannot be in the future")
        return value

    def validate_receipt_image(self, value):
        if not value:
            return value
        max_bytes = getattr(settings, "RECEIPT_MAX_MB", 10) * 1024 * 1024
        allowed_exts = getattr(settings, "RECEIPT_ALLOWED_EXTS", ["jpg", "jpeg", "png", "pdf"])
        if hasattr(value, "size") and value.size > max_bytes:
            raise serializers.ValidationError("Receipt image exceeds maximum size")
        name = getattr(value, "name", "") or ""
        ext = os.path.splitext(name)[1].lower().lstrip(".")
        if ext and allowed_exts and ext not in allowed_exts:
            raise serializers.ValidationError("Unsupported receipt file type")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        description = attrs.get("description")
        if self.instance and description is None:
            description = self.instance.description
        date = attrs.get("date") or (self.instance.date if self.instance else None)
        if user and getattr(user, "is_authenticated", False) and date and description:
            normalized = re.sub(r"\s+", "", description or "").lower()
            if normalized:
                qs = Transaction.objects.filter(user=user, date=date)
                if self.instance:
                    qs = qs.exclude(pk=self.instance.pk)
                for existing in qs[:5]:
                    existing_norm = re.sub(r"\s+", "", (existing.description or "")).lower()
                    if existing_norm and existing_norm == normalized:
                        raise serializers.ValidationError(
                            {"description": serializers.ValidationError("Duplicate transaction suspect", code="duplicate_suspect")}
                        )
        return attrs

    def get_budget(self, obj):
        if obj.budget_id:
            budget = getattr(obj, "budget", None)
            if budget:
                return {"id": budget.id, "name": budget.name}
            return {"id": obj.budget_id, "name": None}
        return None
