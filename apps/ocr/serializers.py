# moved from apps/common/serializers/ocr.py
from rest_framework import serializers

from apps.common.models import OcrApproval
from apps.common.models import OcrValidationLog, Transaction


class ReceiptOCRRequestSerializer(serializers.Serializer):
    transaction_id = serializers.IntegerField(required=False, min_value=1)
    image = serializers.ImageField(required=False, allow_null=True)
    manual_overrides = serializers.DictField(
        child=serializers.CharField(), required=False
    )
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
            raise serializers.ValidationError(
                "transaction_id is required when store=true"
            )

        return attrs


class OcrApprovalSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[OcrApproval.Status.APPROVED, OcrApproval.Status.REJECTED]
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class OcrApprovalDetailSerializer(serializers.ModelSerializer):
    transaction_id = serializers.IntegerField(source="transaction_id", read_only=True)
    transaction = serializers.SerializerMethodField()
    reviewer = serializers.SerializerMethodField()

    class Meta:
        model = OcrApproval
        fields = [
            "transaction_id",
            "status",
            "notes",
            "decided_at",
            "created_at",
            "updated_at",
            "reviewer",
            "transaction",
        ]
        read_only_fields = fields

    def get_transaction(self, obj: OcrApproval):
        tx = obj.transaction
        user = getattr(tx, "user", None)
        return {
            "id": tx.id,
            "date": tx.date,
            "amount": tx.amount,
            "description": tx.description,
            "user": {
                "id": user.id if user else None,
                "username": user.get_username() if user else None,
                "email": getattr(user, "email", None) if user else None,
            },
        }

    def get_reviewer(self, obj: OcrApproval):
        reviewer = obj.reviewer
        if not reviewer:
            return None
        return {
            "id": reviewer.id,
            "username": reviewer.get_username(),
            "email": reviewer.email,
        }


class OcrPendingTransactionSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id",
            "date",
            "amount",
            "description",
            "created_at",
            "updated_at",
            "status",
            "user",
        ]
        read_only_fields = fields

    def get_status(self, obj: Transaction) -> str:
        approval = getattr(obj, "ocr_approval", None)
        if approval and approval.status != OcrApproval.Status.PENDING:
            return approval.status
        return OcrApproval.Status.PENDING

    def get_user(self, obj: Transaction):
        user = getattr(obj, "user", None)
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.get_username(),
            "email": getattr(user, "email", None),
        }


class OcrValidationLogSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = OcrValidationLog
        fields = [
            "id",
            "created_at",
            "updated_at",
            "is_valid",
            "notes",
            "extracted_json",
            "user",
        ]
        read_only_fields = fields

    def get_user(self, obj: OcrValidationLog):
        user = obj.user
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.get_username(),
            "email": getattr(user, "email", None),
        }
