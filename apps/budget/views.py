# moved from apps/common/views/budget.py
from datetime import datetime

from django.db.models import Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.budget.models import Budget
from apps.budget.serializers import BudgetSerializer, BudgetWriteSerializer
from apps.common.filters import BudgetFilter, TransactionFilter
from apps.common.models import Transaction
from apps.common.permissions import IsAdminOrReadOnly
from apps.groups.mixins import GroupContextMixin
from apps.groups.services import user_is_group_admin
from apps.ledger.serializers import TransactionSerializer


class BudgetViewSet(GroupContextMixin, viewsets.ModelViewSet):
    queryset = Budget.objects.select_related("group").all().order_by("name")
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
        context["group"] = self.get_group()
        if hasattr(self, "_budget_usage_map"):
            context["budget_usage"] = self._budget_usage_map
        return context

    def get_queryset(self):
        return (
            Budget.objects.select_related("group")
            .filter(group=self.get_group())
            .order_by("name")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        date_from, date_to = self._parse_date_params(request)
        budgets_for_usage = page if page is not None else queryset
        budgets_list = list(budgets_for_usage)
        self._budget_usage_map = self._build_usage_map(budgets_list, date_from, date_to)
        serializer = self.get_serializer(
            page if page is not None else budgets_list, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        date_from, date_to = self._parse_date_params(request)
        self._budget_usage_map = self._build_usage_map([instance], date_from, date_to)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        self.require_admin()
        serializer.save(group=self.get_group())

    def perform_update(self, serializer):
        self.require_admin()
        if serializer.instance.group_id != self.get_group().id:
            raise ValidationError({"group_id": "Budget belongs to a different group"})
        serializer.save()

    def _parse_date_params(self, request):
        def parse(value, field_name):
            if not value:
                return None
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValidationError(
                    {field_name: "Invalid date format. Use YYYY-MM-DD"}
                ) from exc

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

        qs = Transaction.objects.filter(
            group=self.get_group(), type=Transaction.TransactionType.EXPENSE
        )
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        usage = {}
        if budget_ids:
            for row in (
                qs.filter(budget_id__in=budget_ids)
                .values("budget_id")
                .annotate(total=Sum("amount"))
            ):
                usage[row["budget_id"]] = int(row["total"] or 0)

        if name_to_id:
            categories = list(name_to_id.keys())
            for row in (
                qs.filter(budget__isnull=True, category__in=categories)
                .values("category")
                .annotate(total=Sum("amount"))
            ):
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
        queryset = queryset.filter(group=self.get_group())
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
            fields = [
                field.strip()
                for field in ordering_param.split(",")
                if field.strip() in allowed
            ]
            if fields:
                queryset = queryset.order_by(*fields)
            else:
                queryset = queryset.order_by("-date", "-id")
        else:
            queryset = queryset.order_by("-date", "-id")

        page = self.paginate_queryset(queryset)
        serializer = TransactionSerializer(
            page if page is not None else queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
