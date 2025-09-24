# moved from apps/common/views/openbanking.py
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsAdminOrReadOnly
from apps.openbanking.models import OpenBankingAccount
from apps.openbanking.serializers import (
    OpenBankingAccountSerializer,
    OpenBankingBalanceQuerySerializer,
    OpenBankingTransactionQuerySerializer,
)
from apps.openbanking.services import fetch_balance, fetch_transactions


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


class OpenBankingBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = OpenBankingBalanceQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        fintech_use_num = serializer.validated_data["fintech_use_num"]

        account = OpenBankingAccount.objects.filter(fintech_use_num=fintech_use_num).first()
        if account and not account.enabled:
            raise PermissionDenied("Account is disabled")

        data = fetch_balance(fintech_use_num)
        debug = request.query_params.get("debug") == "1"
        response = {
            "fintech_use_num": fintech_use_num,
            "account": {
                "alias": getattr(account, "alias", None),
                "bank_name": getattr(account, "bank_name", None),
            }
            if account
            else None,
            "balance": data.get("balance_amt"),
            "currency": data.get("currency"),
            "raw": data if debug else None,
        }
        return Response(response, status=status.HTTP_200_OK)


class OpenBankingTransactionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = OpenBankingTransactionQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        fintech_use_num = validated["fintech_use_num"]
        from_date = validated["from_date"]
        to_date = validated["to_date"]
        sort = validated["sort"]
        page = validated["page"]
        size = validated["size"]

        account = OpenBankingAccount.objects.filter(fintech_use_num=fintech_use_num).first()
        if account and not account.enabled:
            raise PermissionDenied("Account is disabled")

        data = fetch_transactions(
            fintech_use_num,
            from_date,
            to_date,
            sort=sort,
            page=page,
            size=size,
        )

        transactions = data.get("res_list") or data.get("list") or []
        debug = request.query_params.get("debug") == "1"
        response = {
            "fintech_use_num": fintech_use_num,
            "range": {"from": from_date, "to": to_date},
            "sort": sort,
            "page": page,
            "size": size,
            "list": transactions,
            "raw": data if debug else None,
        }
        # TODO: integrate transactions into internal ledger (sync mechanism)
        return Response(response, status=status.HTTP_200_OK)
