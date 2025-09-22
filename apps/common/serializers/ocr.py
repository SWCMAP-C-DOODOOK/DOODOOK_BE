# moved from apps/common/serializers.py
from rest_framework import serializers


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
