from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import UserProfileViewSet, UserRoleUpdateAPIView

router = DefaultRouter()
router.register(r'profiles', UserProfileViewSet, basename='user-profile')

urlpatterns = [
    path('users/<int:pk>/role', UserRoleUpdateAPIView.as_view()),
]

urlpatterns += router.urls
