# moved from apps/common/filters.py
from typing import TYPE_CHECKING

import django_filters
from django.apps import apps as django_apps
from django.db.models import Q

from apps.common.models import Transaction

if TYPE_CHECKING:  # pragma: no cover
    from apps.budget.models import Budget  # noqa: F401


class TransactionFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")
    type = django_filters.CharFilter(field_name="type")
    min_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    max_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")
    category = django_filters.CharFilter(field_name="category", lookup_expr="icontains")
    has_receipt = django_filters.BooleanFilter(method="filter_has_receipt")

    class Meta:
        model = Transaction
        fields = ["date", "type", "category"]

    def filter_has_receipt(self, queryset, name, value):
        if value is None:
            return queryset
        if value:
            return queryset.filter(receipt_image__isnull=False).exclude(receipt_image="")
        return queryset.filter(Q(receipt_image__isnull=True) | Q(receipt_image=""))


class BudgetFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = django_apps.get_model("budget", "Budget")
        fields = ["name"]
