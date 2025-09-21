from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminRole(BasePermission):
    """Allow only authenticated users with role 'admin' (fallback to is_staff)."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        role = getattr(user, "role", None)
        return role == "admin" or bool(getattr(user, "is_staff", False))


class IsAdminOrReadOnly(BasePermission):
    """Authenticated users may read; only role 'admin' may write/delete."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        role = getattr(user, "role", None)
        return role == "admin" or bool(getattr(user, "is_staff", False))


class IsOwnerOrAdmin(BasePermission):
    """Object-level check: owner (obj.user) or admin may proceed."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        role = getattr(user, "role", None)
        if role == "admin" or bool(getattr(user, "is_staff", False)):
            return True
        owner = getattr(obj, "user", None)
        return owner == user

