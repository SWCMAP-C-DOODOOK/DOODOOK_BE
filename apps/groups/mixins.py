from rest_framework.exceptions import PermissionDenied

from apps.groups.models import Group, GroupMembership
from apps.groups.services import extract_group_id, resolve_group_and_membership, user_is_group_admin


class GroupContextMixin:
    """
    Resolve a group from request (query params, kwargs, or body) and
    provide convenience helpers for membership checks.
    """

    group_param = "group_id"
    _group_cache = None
    _membership_cache = None

    def get_group_id(self):
        request = getattr(self, "request", None)
        if request is None:
            raise PermissionDenied("Request context missing")
        if hasattr(self, "kwargs") and self.kwargs.get(self.group_param):
            try:
                return int(self.kwargs[self.group_param])
            except (TypeError, ValueError) as exc:
                raise PermissionDenied("Invalid group_id") from exc
        return extract_group_id(request)

    def get_group(self) -> Group:
        if self._group_cache is not None:
            return self._group_cache
        group, membership = resolve_group_and_membership(self.request)
        self._group_cache = group
        self._membership_cache = membership
        setattr(self.request, "group", group)
        setattr(self.request, "group_membership", membership)
        return group

    def get_membership(self) -> GroupMembership:
        if self._membership_cache is not None:
            return self._membership_cache
        _, membership = resolve_group_and_membership(self.request)
        self._membership_cache = membership
        setattr(self.request, "group_membership", membership)
        return membership

    def require_admin(self) -> GroupMembership:
        membership = self.get_membership()
        if not user_is_group_admin(self.request.user, membership):
            raise PermissionDenied("Admin privileges required")
        return membership
