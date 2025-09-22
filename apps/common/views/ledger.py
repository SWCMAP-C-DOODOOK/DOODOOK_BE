# moved from apps/common/views.py
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
from apps.common.serializers import TransactionSerializer


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
    # TODO: apply IsOwnerOrAdmin for limited write access when member self-edit rules introduced

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise ValidationError({"detail": "Authentication required"})
        with db_transaction.atomic():
            serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        if not self.request.user.is_authenticated:
            raise ValidationError({"detail": "Authentication required"})
        with db_transaction.atomic():
            serializer.save()
