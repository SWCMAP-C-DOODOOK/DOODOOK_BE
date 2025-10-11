from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    KakaoCallbackAPIView,
    KakaoLoginAPIView,
    MeAPIView,
    UserProfileViewSet,
    UserRoleUpdateAPIView,
)

router = DefaultRouter()
router.register(r"profiles", UserProfileViewSet, basename="user-profile")

urlpatterns = [
    path("users/<int:pk>/role", UserRoleUpdateAPIView.as_view()),
    path("auth/kakao/login", KakaoLoginAPIView.as_view()),
    path("auth/kakao/callback", KakaoCallbackAPIView.as_view()),
    path("auth/me", MeAPIView.as_view()),
]

urlpatterns += router.urls
