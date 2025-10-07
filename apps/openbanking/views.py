# moved from apps/common/views/openbanking.py
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsAdminOrReadOnly
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


class OpenBankingAccountViewSet(viewsets.ModelViewSet):
    queryset = OpenBankingAccount.objects.all().order_by("alias")
    serializer_class = OpenBankingAccountSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        role = getattr(user, "role", None)
        if role == "admin" or getattr(user, "is_staff", False):
            return queryset
        return queryset.filter(enabled=True)


class _AdminOnlyMixin:
    @staticmethod
    def _require_admin(user) -> None:
        if getattr(user, "is_staff", False) or getattr(user, "role", None) == "admin":
            return
        raise PermissionDenied("Admin access required in demo mode")

    @staticmethod
    def _account_payload(account):
        if not account:
            return {"alias": None, "bank_name": None}
        return {"alias": account.alias, "bank_name": account.bank_name}


class OpenBankingBalanceView(_AdminOnlyMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = OpenBankingBalanceQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        fintech_use_num = serializer.validated_data["fintech_use_num"]

        account = OpenBankingAccount.objects.filter(fintech_use_num=fintech_use_num).first()
        if account and not account.enabled:
            raise PermissionDenied("Account is disabled")

        self._require_admin(request.user)
        payload = fetch_balance(fintech_use_num)
        payload["account"] = self._account_payload(account)

        debug = request.query_params.get("debug") == "1"
        if not debug:
            payload["raw"] = None
        return Response(payload, status=status.HTTP_200_OK)


class OpenBankingTransactionsView(_AdminOnlyMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = OpenBankingTransactionQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        fintech_use_num = validated["fintech_use_num"]

        account = OpenBankingAccount.objects.filter(fintech_use_num=fintech_use_num).first()
        if account and not account.enabled:
            raise PermissionDenied("Account is disabled")

        self._require_admin(request.user)
        payload = fetch_transactions(
            fintech_use_num,
            validated["from_date"],
            validated["to_date"],
            sort=validated["sort"],
            page=validated["page"],
            size=validated["size"],
        )
        payload["account"] = self._account_payload(account)

        debug = request.query_params.get("debug") == "1"
        if not debug:
            payload["raw"] = None
        return Response(payload, status=status.HTTP_200_OK)
