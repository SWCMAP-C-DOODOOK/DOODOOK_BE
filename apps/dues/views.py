import csv
from datetime import datetime
from typing import Tuple

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import Payment
from apps.common.permissions import IsAdminRole
from apps.dues.models import DuesReminder
from apps.dues.serializers import DuesReminderSerializer, DuesReminderUpdateSerializer


User = get_user_model()


def _parse_year_month(params) -> Tuple[int, int]:
    now = timezone.localtime()
    year_raw = params.get("year", now.year)
    month_raw = params.get("month", now.month)

    try:
        year = int(year_raw)
    except (TypeError, ValueError):
        raise ValueError("Year must be an integer")
    try:
        month = int(month_raw)
    except (TypeError, ValueError):
        raise ValueError("Month must be an integer between 1 and 12")

    if year <= 0:
        raise ValueError("Year must be positive")
    if month < 1 or month > 12:
        raise ValueError("Month must be between 1 and 12")

    return year, month


class PaymentTotalsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            year, month = _parse_year_month(request.query_params)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        paid_qs = Payment.objects.filter(year=year, month=month, is_paid=True)
        unpaid_qs = Payment.objects.filter(year=year, month=month).exclude(is_paid=True)

        paid_sum = paid_qs.aggregate(total=Sum("amount"))[
            "total"
        ] or 0
        unpaid_sum = unpaid_qs.aggregate(total=Sum("amount"))[
            "total"
        ] or 0

        return Response(
            {
                "year": year,
                "month": month,
                "paid_sum": int(paid_sum),
                "unpaid_sum": int(unpaid_sum),
            }
        )


class PaymentExportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        try:
            year, month = _parse_year_month(request.query_params)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payments = Payment.objects.select_related("user").filter(year=year, month=month)
        filename = f"dues_{year}_{month:02d}.csv"

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={filename}"

        writer = csv.writer(response)
        writer.writerow(["status", "user", "amount", "paid_at"])

        for payment in payments:
            status_label = "paid" if payment.is_paid else "unpaid"
            writer.writerow(
                [
                    status_label,
                    payment.user.get_username() if payment.user else "",
                    payment.amount or 0,
                    payment.paid_at.isoformat() if payment.paid_at else "",
                ]
            )

        return response


class DuesReminderViewSet(viewsets.ModelViewSet):
    queryset = DuesReminder.objects.select_related("target_user", "created_by").all()
    serializer_class = DuesReminderSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get_serializer_class(self):
        if self.action in {"update", "partial_update"}:
            return DuesReminderUpdateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, status=DuesReminder.Status.PENDING)

    @action(detail=True, methods=["post"], url_path="resend")
    def resend(self, request, pk=None):
        reminder = self.get_object()
        reminder.status = DuesReminder.Status.PENDING
        if "scheduled_at" in request.data:
            try:
                new_time = datetime.fromisoformat(request.data["scheduled_at"])  # type: ignore[arg-type]
            except ValueError:
                return Response({"detail": "Invalid scheduled_at format"}, status=status.HTTP_400_BAD_REQUEST)
            if timezone.is_naive(new_time):
                new_time = timezone.make_aware(new_time, timezone.get_current_timezone())
            reminder.scheduled_at = new_time
        reminder.sent_at = None
        reminder.save(update_fields=["status", "scheduled_at", "sent_at", "updated_at"])
        serializer = self.get_serializer(reminder)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="mark-sent")
    def mark_sent(self, request, pk=None):
        reminder = self.get_object()
        reminder.status = DuesReminder.Status.SENT
        reminder.sent_at = timezone.now()
        reminder.save(update_fields=["status", "sent_at", "updated_at"])
        serializer = self.get_serializer(reminder)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        status_param = request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


__all__ = ["PaymentTotalsView", "PaymentExportView", "DuesReminderViewSet"]
