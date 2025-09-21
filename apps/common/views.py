import os
from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
from django.db.models import Exists, OuterRef, Subquery, Sum, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .filters import BudgetFilter, TransactionFilter
from .models import Budget, OpenBankingAccount, Payment, Transaction
from .serializers import (
    BudgetSerializer,
    BudgetWriteSerializer,
    DuesStatusSerializer,
    OpenBankingAccountSerializer,
    OpenBankingBalanceQuerySerializer,
    OpenBankingTransactionQuerySerializer,
    PaymentSerializer,
    ReceiptOCRRequestSerializer,
    TransactionSerializer,
)
from .services.ocr import OCRServiceError, extract_text_from_image
from .services.openbanking import fetch_balance, fetch_transactions
from .permissions import IsAdminOrReadOnly


User = get_user_model()


def _parse_year_month(params) -> tuple[int, int]:
    now = timezone.localtime()
    year_raw = params.get("year", now.year)
    month_raw = params.get("month", now.month)

    try:
        year = int(year_raw)
    except (TypeError, ValueError):
        raise ValidationError({"year": "Year must be an integer"})
    try:
        month = int(month_raw)
    except (TypeError, ValueError):
        raise ValidationError({"month": "Month must be an integer between 1 and 12"})

    if year <= 0:
        raise ValidationError({"year": "Year must be positive"})
    if month < 1 or month > 12:
        raise ValidationError({"month": "Month must be between 1 and 12"})

    return year, month


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("user").all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        filters = {}

        year_raw = params.get("year")
        month_raw = params.get("month")

        if year_raw is not None:
            try:
                filters["year"] = int(year_raw)
            except (TypeError, ValueError):
                raise ValidationError({"year": "Year must be an integer"})
            if filters["year"] <= 0:
                raise ValidationError({"year": "Year must be positive"})

        if month_raw is not None:
            try:
                month = int(month_raw)
            except (TypeError, ValueError):
                raise ValidationError({"month": "Month must be an integer between 1 and 12"})
            if month < 1 or month > 12:
                raise ValidationError({"month": "Month must be between 1 and 12"})
            filters["month"] = month

        if filters:
            queryset = queryset.filter(**filters)

        return queryset.order_by("-year", "-month", "user__username")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        created = getattr(serializer, "_created", True)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code, headers=headers)


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


class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all().order_by("name")
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = BudgetFilter
    search_fields = ["name", "description"]
    ordering_fields = ["name", "allocated_amount", "created_at", "updated_at"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return BudgetWriteSerializer
        return BudgetSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(self, "_budget_usage_map"):
            context["budget_usage"] = self._budget_usage_map
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        date_from, date_to = self._parse_date_params(request)
        budgets_for_usage = page if page is not None else queryset
        budgets_list = list(budgets_for_usage)
        self._budget_usage_map = self._build_usage_map(budgets_list, date_from, date_to)
        serializer = self.get_serializer(page if page is not None else budgets_list, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        date_from, date_to = self._parse_date_params(request)
        self._budget_usage_map = self._build_usage_map([instance], date_from, date_to)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def _parse_date_params(self, request):
        def parse(value, field_name):
            if not value:
                return None
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValidationError({field_name: "Invalid date format. Use YYYY-MM-DD"}) from exc

        date_from = parse(request.query_params.get("date_from"), "date_from")
        date_to = parse(request.query_params.get("date_to"), "date_to")
        if date_from and date_to and date_from > date_to:
            raise ValidationError({"date": "date_from cannot be later than date_to"})
        return date_from, date_to

    def _build_usage_map(self, budgets, date_from, date_to):
        if not budgets:
            return {}
        budget_ids = [budget.id for budget in budgets if budget.id]
        name_to_id = {budget.name: budget.id for budget in budgets if budget.name}

        qs = Transaction.objects.filter(type=Transaction.TransactionType.EXPENSE)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        usage = {}
        if budget_ids:
            for row in qs.filter(budget_id__in=budget_ids).values("budget_id").annotate(total=Sum("amount")):
                usage[row["budget_id"]] = int(row["total"] or 0)

        if name_to_id:
            categories = list(name_to_id.keys())
            for row in qs.filter(budget__isnull=True, category__in=categories).values("category").annotate(total=Sum("amount")):
                budget_id = name_to_id.get(row["category"])
                if budget_id:
                    usage[budget_id] = usage.get(budget_id, 0) + int(row["total"] or 0)

        return usage

    @action(detail=True, methods=["get"], url_path="transactions")
    def transactions(self, request, pk=None):
        budget = self.get_object()
        date_from, date_to = self._parse_date_params(request)

        queryset = Transaction.objects.select_related("user", "budget").filter(
            Q(budget=budget) | (Q(budget__isnull=True) & Q(category=budget.name))
        )
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        filterset = TransactionFilter(request.query_params, queryset=queryset)
        if not filterset.is_valid():
            raise ValidationError(filterset.errors)
        queryset = filterset.qs

        ordering_param = request.query_params.get("ordering")
        if ordering_param:
            allowed = {"date", "-date", "amount", "-amount", "id", "-id"}
            fields = [field.strip() for field in ordering_param.split(",") if field.strip() in allowed]
            if fields:
                queryset = queryset.order_by(*fields)
            else:
                queryset = queryset.order_by("-date", "-id")
        else:
            queryset = queryset.order_by("-date", "-id")

        page = self.paginate_queryset(queryset)
        serializer = TransactionSerializer(page if page is not None else queryset, many=True, context=self.get_serializer_context())
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


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
            } if account else None,
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


class DuesStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year, month = _parse_year_month(request.query_params)

        payments = Payment.objects.filter(user=OuterRef("pk"), year=year, month=month)
        paid_queryset = payments.filter(is_paid=True)

        users = (
            User.objects.all()
            .annotate(
                paid=Exists(paid_queryset),
                paid_amount=Subquery(paid_queryset.values("amount")[:1]),
                paid_timestamp=Subquery(paid_queryset.values("paid_at")[:1]),
            )
            .order_by("username")
        )

        data = [
            {
                "user_id": user.id,
                "username": user.get_username(),
                "paid": bool(getattr(user, "paid", False)),
                "amount": user.paid_amount if getattr(user, "paid", False) else None,
                "paid_at": user.paid_timestamp if getattr(user, "paid", False) else None,
            }
            for user in users
        ]

        serializer = DuesStatusSerializer(instance=data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DuesUnpaidView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year, month = _parse_year_month(request.query_params)

        payments = Payment.objects.filter(user=OuterRef("pk"), year=year, month=month, is_paid=True)
        users = (
            User.objects.all()
            .annotate(paid=Exists(payments))
            .filter(paid=False)
            .order_by("username")
        )

        data = [
            {"user_id": user.id, "username": user.get_username()}
            for user in users
        ]

        return Response(data, status=status.HTTP_200_OK)


class ReceiptOCRView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        for key in ("transaction_id", "store", "overwrite"):
            if key not in data and key in request.query_params:
                data[key] = request.query_params[key]

        has_image = bool(request.FILES.get("image"))
        serializer = ReceiptOCRRequestSerializer(data=data, context={"has_image": has_image})
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        transaction = None
        transaction_id = validated.get("transaction_id")
        store = validated.get("store", False)
        overwrite = validated.get("overwrite", False)
        source = "uploaded" if has_image else "transaction"

        image_file = None
        if has_image:
            image_file = request.FILES.get("image")
            content_type = getattr(image_file, "content_type", "") or ""
            if content_type and not content_type.startswith("image/"):
                raise ValidationError({"image": "Only image files are supported"})
            if hasattr(image_file, "size") and image_file.size == 0:
                raise ValidationError({"image": "Empty image file"})

        if transaction_id:
            transaction = get_object_or_404(Transaction.objects.select_related("user"), pk=transaction_id)
            if not has_image:
                if not transaction.receipt_image:
                    return Response({"detail": "Receipt image not found for transaction"}, status=status.HTTP_400_BAD_REQUEST)
                image_file = transaction.receipt_image
                source = "transaction"

        if image_file is None:
            raise ValidationError({"detail": "Image source not found"})

        api_key = os.environ.get("KAKAO_REST_API_KEY", "")

        needs_close = False
        if hasattr(image_file, "open") and getattr(image_file, "closed", True):
            image_file.open("rb")
            needs_close = True

        try:
            text = extract_text_from_image(image_file, api_key)
        except OCRServiceError as exc:
            return Response({"detail": str(exc)}, status=exc.status_code)
        finally:
            if needs_close and hasattr(image_file, "close"):
                image_file.close()

        stored = False
        if store:
            if not transaction:
                return Response({"detail": "transaction_id is required to store OCR text"}, status=status.HTTP_400_BAD_REQUEST)
            is_admin_role = getattr(request.user, "role", None) == "admin" or getattr(request.user, "is_staff", False)
            if not (is_admin_role or transaction.user_id == request.user.id):
                return Response({"detail": "Not authorized to store OCR result"}, status=status.HTTP_403_FORBIDDEN)
            if transaction.ocr_text and not overwrite:
                return Response({"detail": "OCR text already exists. Pass overwrite=true to replace."}, status=status.HTTP_409_CONFLICT)

            with db_transaction.atomic():
                transaction.ocr_text = text
                transaction.save(update_fields=["ocr_text", "updated_at"])
            stored = True
            # TODO: leverage IsOwnerOrAdmin permission for store workflow to centralize checks

        return Response(
            {
                "transaction_id": transaction_id,
                "text": text,
                "stored": stored,
                "source": source,
            },
            status=status.HTTP_200_OK,
        )
