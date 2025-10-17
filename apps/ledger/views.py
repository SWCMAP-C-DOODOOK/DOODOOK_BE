from django.db import transaction as db_transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from apps.common.filters import TransactionFilter
from apps.common.models import Transaction
from apps.common.permissions import IsAdminOrReadOnly
from apps.ledger.models import LedgerAuditLog
from apps.ledger.serializers import TransactionSerializer
from apps.groups.mixins import GroupContextMixin
from apps.groups.services import get_active_membership, user_is_group_admin


class TransactionViewSet(GroupContextMixin, viewsets.ModelViewSet):
    queryset = Transaction.objects.select_related("user", "budget", "group").all()
    serializer_class = TransactionSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = TransactionFilter
    search_fields = ["description", "category"]
    ordering_fields = ["date", "amount", "id"]
    ordering = ["-date", "-id"]
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        group = self.get_group()
        queryset = (
            Transaction.objects.select_related("user", "budget", "group")
            .filter(group=group)
            .order_by("-date", "-id")
        )
        tab = self.request.query_params.get("tab")
        if tab == "income":
            queryset = queryset.filter(type=Transaction.TransactionType.INCOME)
        elif tab == "expense":
            queryset = queryset.filter(type=Transaction.TransactionType.EXPENSE)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["group"] = self.get_group()
        return context

    def _serialize_transaction(self, instance):
        return {
            "id": instance.id,
            "group_id": instance.group_id,
            "user_id": instance.user_id,
            "budget_id": instance.budget_id,
            "amount": instance.amount,
            "description": instance.description,
            "date": instance.date.isoformat() if instance.date else None,
            "type": instance.type,
            "category": instance.category,
            "receipt_image": (
                instance.receipt_image.name if instance.receipt_image else None
            ),
        }

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise ValidationError({"detail": "Authentication required"})
        group = self.get_group()
        membership = get_active_membership(group, self.request.user)
        if membership is None:
            raise ValidationError({"detail": "Group membership required"})
        with db_transaction.atomic():
            instance = serializer.save(user=self.request.user, group=group, membership=membership)
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
            if old_instance.group_id != self.get_group().id:
                raise ValidationError({"detail": "Cannot move transaction between groups"})
            membership = get_active_membership(self.get_group(), serializer.instance.user)
            if membership is None:
                raise ValidationError({"detail": "Target user is not active member"})
            old_snapshot = self._serialize_transaction(old_instance)
            instance = serializer.save(membership=membership)
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
        if instance.group_id != self.get_group().id:
            raise PermissionDenied("Invalid group context")
        membership = self.get_membership()
        if not user_is_group_admin(self.request.user, membership, self.get_group()):
            raise PermissionDenied("Admin privileges required to delete transactions")
        snapshot = self._serialize_transaction(instance)
        LedgerAuditLog.objects.create(
            transaction=instance,
            user=self.request.user if self.request.user.is_authenticated else None,
            action=LedgerAuditLog.Action.DELETE,
            diff_json={"old": snapshot},
        )
        super().perform_destroy(instance)
