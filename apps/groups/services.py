import random
import string
from typing import Optional

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.groups.models import Group, GroupMembership


def extract_group_id(request) -> int:
    """
    Try to resolve group_id from request kwargs, query params, or data.
    Raises ValidationError if missing or invalid.
    """
    group_id = None

    if hasattr(request, "parser_context"):
        kwargs = request.parser_context.get("kwargs") if request.parser_context else {}
        if kwargs and kwargs.get("group_id"):
            group_id = kwargs.get("group_id")

    if group_id is None and request.query_params.get("group_id"):
        group_id = request.query_params.get("group_id")

    if group_id is None and isinstance(getattr(request, "data", None), dict):
        group_id = request.data.get("group_id")

    if not group_id:
        raise ValidationError({"group_id": "group_id is required"})

    try:
        return int(group_id)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"group_id": "Invalid group_id"}) from exc


def resolve_group_and_membership(request) -> tuple[Group, GroupMembership]:
    group_id = extract_group_id(request)
    group = get_object_or_404(Group, pk=group_id)
    if not request.user or not request.user.is_authenticated:
        raise PermissionDenied("Authentication required for group access")
    membership = GroupMembership.objects.filter(
        group=group,
        user=request.user,
        status=GroupMembership.Status.ACTIVE,
    ).first()
    if membership is None and not getattr(request.user, "is_staff", False):
        raise PermissionDenied("Group membership required")
    setattr(request, "group", group)
    setattr(request, "group_membership", membership)
    return group, membership


def get_active_membership(group: Group, user) -> Optional[GroupMembership]:
    return GroupMembership.objects.filter(
        group=group,
        user=user,
        status=GroupMembership.Status.ACTIVE,
    ).first()


def resolve_group_with_default(request) -> tuple[Group, Optional[GroupMembership]]:
    try:
        group_id = extract_group_id(request)
    except ValidationError:
        group_id = None

    if group_id:
        return resolve_group_and_membership(request)

    membership = (
        GroupMembership.objects.filter(
            user=request.user,
            status=GroupMembership.Status.ACTIVE,
        )
        .select_related("group")
        .order_by("group__name")
        .first()
    )
    if membership is None:
        raise ValidationError({"group_id": "활성화된 그룹이 없습니다."})

    group = membership.group
    setattr(request, "group", group)
    setattr(request, "group_membership", membership)
    return group, membership


def user_is_group_admin(
    user, membership: Optional[GroupMembership], group: Optional[Group] = None
) -> bool:
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True
    if membership:
        return membership.role == GroupMembership.Roles.ADMIN
    if group:
        # fallback check if membership not provided
        return GroupMembership.objects.filter(
            group=group,
            user=user,
            role=GroupMembership.Roles.ADMIN,
            status=GroupMembership.Status.ACTIVE,
        ).exists()
    return False


def generate_invite_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=length))
