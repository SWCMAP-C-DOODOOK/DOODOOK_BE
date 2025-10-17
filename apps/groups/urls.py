from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.groups.views import DashboardAPIView, GroupMembershipViewSet, GroupViewSet

router = DefaultRouter()
router.register(r"groups", GroupViewSet, basename="group")
router.register(r"group-memberships", GroupMembershipViewSet, basename="group-membership")

urlpatterns = [
    path("dashboard", DashboardAPIView.as_view(), name="dashboard"),
]

urlpatterns += router.urls
