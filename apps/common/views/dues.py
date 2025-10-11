# moved from apps/common/views.py
from typing import Tuple

from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Subquery
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import Payment
from apps.common.permissions import IsAdminOrReadOnly
from apps.common.serializers import DuesStatusSerializer, PaymentSerializer

User = get_user_model()


def _parse_year_month(params) -> Tuple[int, int]:
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
                raise ValidationError(
                    {"month": "Month must be an integer between 1 and 12"}
                )
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
                "paid_at": (
                    user.paid_timestamp if getattr(user, "paid", False) else None
                ),
            }
            for user in users
        ]

        serializer = DuesStatusSerializer(instance=data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DuesUnpaidView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year, month = _parse_year_month(request.query_params)

        payments = Payment.objects.filter(
            user=OuterRef("pk"), year=year, month=month, is_paid=True
        )
        users = (
            User.objects.all()
            .annotate(paid=Exists(payments))
            .filter(paid=False)
            .order_by("username")
        )

        data = [{"user_id": user.id, "username": user.get_username()} for user in users]

        return Response(data, status=status.HTTP_200_OK)
