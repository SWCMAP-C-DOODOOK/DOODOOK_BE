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
from apps.groups.mixins import GroupContextMixin
from apps.groups.models import GroupMembership
from apps.groups.services import get_active_membership, resolve_group_with_default
from apps.users.serializers import UserSerializer
from apps.common.serializers import (
    DuesStatusSerializer,
    PaymentAdminSerializer,
    PaymentSerializer,
)

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


class PaymentViewSet(GroupContextMixin, viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("user", "group").all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        group = self.get_group()
        params = self.request.query_params
        queryset = (
            Payment.objects.select_related("user", "group")
            .filter(group=group)
            .order_by("-year", "-month", "user__username")
        )
        user_param = params.get("user_id")
        if user_param:
            queryset = queryset.filter(user_id=user_param)
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

        return queryset

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return PaymentAdminSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            context["group"] = self.get_group()
        except ValidationError:
            pass
        return context

    def create(self, request, *args, **kwargs):
        self.require_admin()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = self.get_group()
        membership = get_active_membership(group, serializer.validated_data.get("user"))
        if membership is None:
            raise ValidationError({"user_id": "User is not an active member of the group"})
        serializer.save(group=group, membership=membership)
        headers = self.get_success_headers(serializer.data)
        created = getattr(serializer, "_created", True)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code, headers=headers)

    def list(self, request, *args, **kwargs):
        self.require_admin()
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        self.require_admin()
        return super().retrieve(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["group"] = self.get_group()
        return context


class DuesStatusView(GroupContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        self.require_admin()
        year, month = _parse_year_month(request.query_params)
        group = self.get_group()

        payments = Payment.objects.filter(
            group=group, user=OuterRef("pk"), year=year, month=month
        )
        paid_queryset = payments.filter(is_paid=True)

        users = (
            User.objects.filter(
                group_memberships__group=group,
                group_memberships__status=GroupMembership.Status.ACTIVE,
            )
            .annotate(
                paid=Exists(paid_queryset),
                paid_amount=Subquery(paid_queryset.values("amount")[:1]),
                paid_timestamp=Subquery(paid_queryset.values("paid_at")[:1]),
            )
            .order_by("username")
        )

        membership_map = {
            membership.user_id: membership
            for membership in GroupMembership.objects.filter(
                group=group,
                status=GroupMembership.Status.ACTIVE,
            ).select_related("user")
        }

        data = []
        for user in users:
            membership = membership_map.get(user.id)
            payload = {
                "user": {
                    "id": user.id,
                    "username": user.get_username(),
                    "email": user.email,
                    "phone_number": getattr(user, "phone_number", None),
                    "role": getattr(membership, "role", None),
                },
                "paid": bool(getattr(user, "paid", False)),
                "amount": user.paid_amount if getattr(user, "paid", False) else None,
                "paid_at": user.paid_timestamp if getattr(user, "paid", False) else None,
            }
            data.append(payload)

        serializer = DuesStatusSerializer(instance=data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DuesUnpaidView(GroupContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        self.require_admin()
        year, month = _parse_year_month(request.query_params)
        group = self.get_group()

        payments = Payment.objects.filter(
            group=group, user=OuterRef("pk"), year=year, month=month, is_paid=True
        )
        users = (
            User.objects.filter(
                group_memberships__group=group,
                group_memberships__status=GroupMembership.Status.ACTIVE,
            )
            .annotate(paid=Exists(payments))
            .filter(paid=False)
            .order_by("username")
        )

        data = [
            {"user_id": user.id, "username": user.get_username()} for user in users
        ]

        return Response(data, status=status.HTTP_200_OK)


class MyDuesHistoryView(GroupContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        group, membership = resolve_group_with_default(request)
        if membership is None:
            membership = get_active_membership(group, request.user)
        if membership is None:
            raise ValidationError({"detail": "그룹 구성원이 아닙니다."})
        year, month = _parse_year_month(request.query_params)
        queryset = (
            Payment.objects.filter(group=group, user=request.user, year=year, month=month)
            .order_by("-paid_at")
        )
        serializer = PaymentSerializer(queryset, many=True, context={"group": group})
        return Response(serializer.data)
