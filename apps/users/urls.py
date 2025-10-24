from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

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
    path("auth/jwt/refresh", TokenRefreshView.as_view(), name="token_refresh"),
]

urlpatterns += router.urls
