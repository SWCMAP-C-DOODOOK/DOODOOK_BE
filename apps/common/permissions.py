from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.exceptions import ValidationError

from apps.groups.services import resolve_group_and_membership, user_is_group_admin


class IsAdminRole(BasePermission):
    """Allow only authenticated users with role 'admin' (fallback to is_staff)."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        try:
            group, membership = resolve_group_and_membership(request)
        except ValidationError:
            # Non group-specific endpoints fallback to staff/admin flags
            return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
        except Exception:
            return False
        return user_is_group_admin(user, membership, group)


class IsAdminOrReadOnly(BasePermission):
    """Authenticated users may read; only role 'admin' may write/delete."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        try:
            group, membership = resolve_group_and_membership(request)
        except ValidationError:
            return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
        except Exception:
            return False
        return user_is_group_admin(user, membership, group)


class IsOwnerOrAdmin(BasePermission):
    """Object-level check: owner (obj.user) or admin may proceed."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        try:
            group, membership = resolve_group_and_membership(request)
        except ValidationError:
            membership = None
            group = None
        except Exception:
            return False
        if user_is_group_admin(user, membership, group):
            return True
        owner = getattr(obj, "user", None)
        return owner == user
