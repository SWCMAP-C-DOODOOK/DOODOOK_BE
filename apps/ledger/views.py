from django.db import transaction as db_transaction
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.common.filters import TransactionFilter
from apps.common.models import Transaction
from apps.common.permissions import IsAdminOrReadOnly
from apps.ledger.models import LedgerAuditLog
from apps.ledger.serializers import TransactionSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.select_related("user", "budget").all()
    serializer_class = TransactionSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = TransactionFilter
    search_fields = ["description", "category"]
    ordering_fields = ["date", "amount", "id"]
    ordering = ["-date", "-id"]
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def _serialize_transaction(self, instance):
        return {
            "id": instance.id,
            "user_id": instance.user_id,
            "budget_id": instance.budget_id,
            "amount": instance.amount,
            "description": instance.description,
            "date": instance.date.isoformat() if instance.date else None,
            "type": instance.type,
            "category": instance.category,
            "receipt_image": instance.receipt_image.name if instance.receipt_image else None,
        }

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise ValidationError({"detail": "Authentication required"})
        with db_transaction.atomic():
            instance = serializer.save(user=self.request.user)
            LedgerAuditLog.objects.create(
                transaction=instance,
                user=self.request.user,
                action=LedgerAuditLog.Action.CREATE,
                diff_json={"new": self._serialize_transaction(instance)},
            )

    def perform_update(self, serializer):
        if not self.request.user.is_authenticated:
            raise ValidationError({"detail": "Authentication required"})
        with db_transaction.atomic():
            old_instance = serializer.instance
            old_snapshot = self._serialize_transaction(old_instance)
            instance = serializer.save()
            LedgerAuditLog.objects.create(
                transaction=instance,
                user=self.request.user,
                action=LedgerAuditLog.Action.UPDATE,
                diff_json={
                    "old": old_snapshot,
                    "new": self._serialize_transaction(instance),
                },
            )

    def perform_destroy(self, instance):
        snapshot = self._serialize_transaction(instance)
        LedgerAuditLog.objects.create(
            transaction=instance,
            user=self.request.user if self.request.user.is_authenticated else None,
            action=LedgerAuditLog.Action.DELETE,
            diff_json={"old": snapshot},
        )
        super().perform_destroy(instance)
