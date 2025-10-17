# moved from apps/common/views/openbanking.py
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsAdminOrReadOnly
from apps.groups.mixins import GroupContextMixin
from apps.groups.services import user_is_group_admin
from apps.openbanking.models import OpenBankingAccount
from apps.openbanking.serializers import (
    OpenBankingAccountSerializer,
    OpenBankingAuthCallbackSerializer,
    OpenBankingBalanceQuerySerializer,
    OpenBankingTransactionQuerySerializer,
)
from apps.openbanking.services import fetch_balance, fetch_transactions


class OpenBankingCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        serializer = OpenBankingAuthCallbackSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        response = {
            "code": validated["code"],
            "state": validated.get("state"),
            "scope": validated.get("scope"),
            "redirect_uri": getattr(settings, "OPENBANKING_REDIRECT_URI", ""),
        }
        return Response(response, status=status.HTTP_200_OK)


class OpenBankingAccountViewSet(GroupContextMixin, viewsets.ModelViewSet):
    queryset = OpenBankingAccount.objects.select_related("group").all()
    serializer_class = OpenBankingAccountSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        group = self.get_group()
        membership = self.get_membership()
        queryset = queryset.filter(group=group)
        if user_is_group_admin(user, membership, group):
            return queryset
        return queryset.filter(enabled=True)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["group"] = self.get_group()
        return context

    def perform_create(self, serializer):
        self.require_admin()
        serializer.save(group=self.get_group())

    def perform_update(self, serializer):
        self.require_admin()
        if serializer.instance.group_id != self.get_group().id:
            raise PermissionDenied("Account belongs to a different group")
        serializer.save()


def _account_payload(account):
    if not account:
        return {"alias": None, "bank_name": None}
    return {"alias": account.alias, "bank_name": account.bank_name}


class OpenBankingBalanceView(GroupContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        group = self.get_group()
        serializer = OpenBankingBalanceQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        fintech_use_num = serializer.validated_data["fintech_use_num"]

        account = OpenBankingAccount.objects.filter(
            group=group, fintech_use_num=fintech_use_num
        ).first()
        if account and not account.enabled:
            raise PermissionDenied("Account is disabled")

        self.require_admin()
        payload = fetch_balance(fintech_use_num)
        payload["account"] = _account_payload(account)

        debug = request.query_params.get("debug") == "1"
        if not debug:
            payload["raw"] = None
        return Response(payload, status=status.HTTP_200_OK)


class OpenBankingTransactionsView(GroupContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        group = self.get_group()
        serializer = OpenBankingTransactionQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        fintech_use_num = validated["fintech_use_num"]

        account = OpenBankingAccount.objects.filter(
            group=group, fintech_use_num=fintech_use_num
        ).first()
        if account and not account.enabled:
            raise PermissionDenied("Account is disabled")

        self.require_admin()
        payload = fetch_transactions(
            fintech_use_num,
            validated["from_date"],
            validated["to_date"],
            sort=validated["sort"],
            page=validated["page"],
            size=validated["size"],
        )
        payload["account"] = _account_payload(account)

        debug = request.query_params.get("debug") == "1"
        if not debug:
            payload["raw"] = None
        return Response(payload, status=status.HTTP_200_OK)
