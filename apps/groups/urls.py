from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.groups.views import (
    DashboardAPIView,
    GroupInviteCodeView,
    GroupJoinView,
    GroupLeaveView,
    GroupMembershipViewSet,
    GroupViewSet,
)

router = DefaultRouter()
router.register(r"groups", GroupViewSet, basename="group")
router.register(r"group-memberships", GroupMembershipViewSet, basename="group-membership")

urlpatterns = [
    path("dashboard", DashboardAPIView.as_view(), name="dashboard"),
    path("groups/<int:pk>/invite-code", GroupInviteCodeView.as_view(), name="group-invite-code"),
    path("groups/join", GroupJoinView.as_view(), name="group-join"),
    path("groups/<int:pk>/leave", GroupLeaveView.as_view(), name="group-leave"),
]

urlpatterns += router.urls
