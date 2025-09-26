# moved from apps/common/serializers/ocr.py
from rest_framework import serializers

from apps.common.models import OcrApproval


class ReceiptOCRRequestSerializer(serializers.Serializer):
    transaction_id = serializers.IntegerField(required=False, min_value=1)
    image = serializers.ImageField(required=False, allow_null=True)
    provider = serializers.ChoiceField(choices=["google", "kakao"], default="google")
    manual_overrides = serializers.DictField(child=serializers.CharField(), required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    store = serializers.BooleanField(required=False, default=False)
    overwrite = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        has_image = self.context.get("has_image", False) or bool(attrs.get("image"))
        transaction_id = attrs.get("transaction_id")
        store = attrs.get("store", False)

        if not transaction_id and not has_image:
            raise serializers.ValidationError("Provide transaction_id or upload image")

        if store and not transaction_id:
            raise serializers.ValidationError("transaction_id is required when store=true")

        return attrs


class OcrApprovalSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[OcrApproval.Status.APPROVED, OcrApproval.Status.REJECTED])
    notes = serializers.CharField(required=False, allow_blank=True)
