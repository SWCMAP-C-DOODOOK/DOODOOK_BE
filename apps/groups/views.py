from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import Payment, Transaction
from apps.openbanking.models import OpenBankingAccount
from apps.openbanking.services import fetch_balance
from apps.groups.models import Group, GroupMembership
from apps.groups.serializers import (
    GroupCreateSerializer,
    GroupJoinSerializer,
    GroupMembershipMutationSerializer,
    GroupMembershipSerializer,
    GroupSerializer,
)
from apps.groups.services import (
    generate_invite_code,
    get_active_membership,
    resolve_group_with_default,
    user_is_group_admin,
)


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.prefetch_related("memberships").all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Group.objects.prefetch_related("memberships", "memberships__user")
            .filter(memberships__user=user, memberships__status=GroupMembership.Status.ACTIVE)
            .distinct()
            .order_by("name", "id")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return GroupCreateSerializer
        return GroupSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        group = serializer.instance
        self._require_admin(group)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        group = self.get_object()
        self._require_admin(group)
        return super().destroy(request, *args, **kwargs)

    def _require_admin(self, group: Group):
        membership = group.memberships.filter(
            user=self.request.user, status=GroupMembership.Status.ACTIVE
        ).first()
        if self.request.user.is_staff or getattr(self.request.user, "is_superuser", False):
            return
        if membership is None or membership.role != GroupMembership.Roles.ADMIN:
            raise PermissionDenied("그룹 관리자만 수정할 수 있습니다.")


class GroupMembershipViewSet(viewsets.ModelViewSet):
    queryset = GroupMembership.objects.select_related("group", "user").all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        group = self._get_group()
        return (
            GroupMembership.objects.select_related("group", "user")
            .filter(group=group)
            .order_by("user__username")
        )

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return GroupMembershipMutationSerializer
        return GroupMembershipSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def list(self, request, *args, **kwargs):
        group = self._get_group()
        self._ensure_member(group)
        queryset = self.get_queryset()
        serializer = GroupMembershipSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        membership = self.get_object()
        self._ensure_member(membership.group)
        serializer = GroupMembershipSerializer(membership, context=self.get_serializer_context())
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        group = self._get_group()
        self._ensure_admin(group)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        User = get_user_model()
        try:
            user = User.objects.get(pk=data["user_id"])
        except User.DoesNotExist as exc:
            raise ValidationError({"user_id": "존재하지 않는 사용자입니다."}) from exc
        role = data.get("role", GroupMembership.Roles.MEMBER)
        status_val = data.get("status", GroupMembership.Status.ACTIVE)
        defaults = {
            "role": role,
            "status": status_val,
            "invited_by": request.user,
        }
        if status_val == GroupMembership.Status.ACTIVE:
            defaults.setdefault("joined_at", timezone.now())
        membership, created = GroupMembership.objects.get_or_create(
            group=group,
            user=user,
            defaults=defaults,
        )
        if not created:
            updated_fields = []
            if "role" in data:
                membership.role = role
                updated_fields.append("role")
            if "status" in data:
                membership.status = status_val
                updated_fields.append("status")
            if membership.status == GroupMembership.Status.ACTIVE and not membership.joined_at:
                membership.joined_at = timezone.now()
                updated_fields.append("joined_at")
            if updated_fields:
                updated_fields.append("updated_at")
                membership.save(update_fields=list(set(updated_fields)))
        output = GroupMembershipSerializer(membership, context=self.get_serializer_context())
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(output.data, status=status_code)

    def partial_update(self, request, *args, **kwargs):
        membership = self.get_object()
        self._ensure_admin(membership.group)
        serializer = self.get_serializer(instance=membership, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        updated_fields = []
        if "role" in data:
            membership.role = data["role"]
            updated_fields.append("role")
        if "status" in data:
            membership.status = data["status"]
            if membership.status == GroupMembership.Status.ACTIVE and not membership.joined_at:
                membership.joined_at = timezone.now()
                updated_fields.append("joined_at")
            updated_fields.append("status")
        if updated_fields:
            updated_fields.append("updated_at")
            membership.save(update_fields=list(set(updated_fields)))
        output = GroupMembershipSerializer(membership, context=self.get_serializer_context())
        return Response(output.data)

    def destroy(self, request, *args, **kwargs):
        membership = self.get_object()
        self._ensure_admin(membership.group)
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_group(self) -> Group:
        group_id = self.request.query_params.get("group_id") or self.request.data.get("group_id")
        if not group_id:
            lookup = self.kwargs.get(self.lookup_field)
            if lookup:
                membership = GroupMembership.objects.select_related("group").filter(pk=lookup).first()
                if membership:
                    return membership.group
            raise ValidationError({"group_id": "group_id 파라미터가 필요합니다."})
        try:
            group = Group.objects.get(pk=group_id)
        except Group.DoesNotExist as exc:
            raise ValidationError({"group_id": "존재하지 않는 그룹입니다."}) from exc
        return group

    def _ensure_member(self, group: Group):
        if self.request.user.is_staff or getattr(self.request.user, "is_superuser", False):
            return
        exists = GroupMembership.objects.filter(
            group=group,
            user=self.request.user,
            status=GroupMembership.Status.ACTIVE,
        ).exists()
        if not exists:
            raise PermissionDenied("그룹 구성원만 접근할 수 있습니다.")

    def _ensure_admin(self, group: Group):
        if self.request.user.is_staff or getattr(self.request.user, "is_superuser", False):
            return
        membership = GroupMembership.objects.filter(
            group=group,
            user=self.request.user,
            status=GroupMembership.Status.ACTIVE,
        ).first()
        if membership is None or membership.role != GroupMembership.Roles.ADMIN:
            raise PermissionDenied("그룹 관리자만 변경할 수 있습니다.")


class GroupInviteCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        membership = get_active_membership(group, request.user)
        if not user_is_group_admin(request.user, membership, group):
            raise PermissionDenied("그룹 관리자만 초대 코드를 확인할 수 있습니다.")
        if not group.invite_code:
            for _ in range(10):
                candidate = generate_invite_code()
                if not Group.objects.filter(invite_code=candidate).exists():
                    group.invite_code = candidate
                    group.save(update_fields=["invite_code", "updated_at"])
                    break
            else:
                raise ValidationError({"detail": "초대 코드를 생성할 수 없습니다. 다시 시도해주세요."})
        payload = {"group_id": group.id, "invite_code": group.invite_code}
        if group.invite_code_expires_at:
            payload["invite_code_expires_at"] = group.invite_code_expires_at
        return Response(payload, status=status.HTTP_200_OK)


class GroupJoinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GroupJoinSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        output = GroupMembershipSerializer(
            membership, context={"request": request}
        )
        status_code = (
            status.HTTP_201_CREATED
            if getattr(serializer, "_created", False)
            else status.HTTP_200_OK
        )
        return Response(output.data, status=status_code)


class GroupLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        membership = GroupMembership.objects.filter(
            group=group,
            user=request.user,
            status=GroupMembership.Status.ACTIVE,
        ).first()
        if membership is None:
            raise ValidationError({"detail": "그룹 구성원이 아닙니다."})
        if membership.role == GroupMembership.Roles.ADMIN and not (
            request.user.is_staff or getattr(request.user, "is_superuser", False)
        ):
            has_other_admin = GroupMembership.objects.filter(
                group=group,
                status=GroupMembership.Status.ACTIVE,
                role=GroupMembership.Roles.ADMIN,
            ).exclude(pk=membership.pk).exists()
            if not has_other_admin:
                raise PermissionDenied("마지막 그룹 관리자는 탈퇴할 수 없습니다.")
        membership.status = GroupMembership.Status.LEFT
        membership.left_at = timezone.now()
        membership.save(update_fields=["status", "left_at", "updated_at"])
        payload = {
            "group_id": group.id,
            "status": membership.status,
            "left_at": membership.left_at,
        }
        return Response(payload, status=status.HTTP_200_OK)


def _serialize_transactions(queryset):
    return [
        {
            "id": tx.id,
            "date": tx.date,
            "amount": tx.amount,
            "type": tx.type,
            "description": tx.description,
            "category": tx.category,
            "user": tx.user.get_username() if tx.user else None,
        }
        for tx in queryset
    ]


def _build_dashboard_payload(group):
    tx_qs = (
        Transaction.objects.select_related("user", "budget")
        .filter(group=group)
        .order_by("-date", "-id")
    )
    recent = {
        "all": _serialize_transactions(tx_qs[:8]),
        "income": _serialize_transactions(
            tx_qs.filter(type=Transaction.TransactionType.INCOME)[:8]
        ),
        "expense": _serialize_transactions(
            tx_qs.filter(type=Transaction.TransactionType.EXPENSE)[:8]
        ),
    }

    income_total = (
        Transaction.objects.filter(
            group=group, type=Transaction.TransactionType.INCOME
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    expense_total = (
        Transaction.objects.filter(
            group=group, type=Transaction.TransactionType.EXPENSE
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    balance = None
    account = (
        OpenBankingAccount.objects.filter(group=group, enabled=True)
        .order_by("-updated_at")
        .first()
    )
    if account:
        try:
            balance_payload = fetch_balance(account.fintech_use_num)
            balance = balance_payload.get("balance")
            if isinstance(balance, str):
                balance = int(balance.replace(",", ""))
        except Exception:
            balance = None
    if balance is None:
        balance = int(income_total) - int(expense_total)

    current = timezone.localdate()
    paid_count = Payment.objects.filter(
        group=group, year=current.year, month=current.month, is_paid=True
    ).count()
    unpaid_count = (
        Payment.objects.filter(
            group=group, year=current.year, month=current.month
        )
        .exclude(is_paid=True)
        .count()
    )

    return {
        "group": {"id": group.id, "name": group.name},
        "balance": balance,
        "recent_transactions": recent,
        "stats": {
            "period": {
                "start": current.replace(day=1),
                "end": current,
            },
            "income_total": int(income_total),
            "expense_total": int(expense_total),
        },
        "dues_summary": {
            "year": current.year,
            "month": current.month,
            "paid_count": paid_count,
            "unpaid_count": unpaid_count,
        },
    }


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        group, membership = resolve_group_with_default(request)
        if membership is None and not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied("그룹 구성원만 조회할 수 있습니다.")
        data = _build_dashboard_payload(group)
        return Response(data)
