import os
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.permissions import IsAdminRole
from apps.groups.models import GroupMembership
from apps.groups.services import resolve_group_and_membership, user_is_group_admin

from .models import UserProfile
from .serializers import RoleUpdateSerializer, UserProfileSerializer, UserSerializer
from .services.kakao import KakaoServiceError, exchange_code_for_token, fetch_user_me


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.select_related("user").all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff or getattr(user, "is_superuser", False):
            return queryset
        return queryset.filter(user=user)

    def perform_create(self, serializer):
        # Admin-only create; attach a user explicitly if provided, otherwise default to request.user
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)

    def perform_update(self, serializer):
        profile = serializer.instance
        user = self.request.user
        if not (user.is_staff or getattr(user, "is_superuser", False)):
            if profile.user_id != user.id:
                raise PermissionDenied("다른 사용자의 프로필은 수정할 수 없습니다.")
        serializer.save()


class UserRoleUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def patch(self, request, pk):
        user_model = get_user_model()
        target_user = get_object_or_404(user_model, pk=pk)
        serializer = RoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group, requester_membership = resolve_group_and_membership(request)
        if not user_is_group_admin(request.user, requester_membership, group):
            raise PermissionDenied("Admin privileges required")

        role = serializer.validated_data["role"]
        membership, _created = GroupMembership.objects.get_or_create(
            group=group,
            user=target_user,
            defaults={
                "role": role,
                "status": GroupMembership.Status.ACTIVE,
                "joined_at": timezone.now(),
                "invited_by": request.user,
            },
        )
        if not _created:
            membership.role = role
            if membership.status != GroupMembership.Status.ACTIVE:
                membership.status = GroupMembership.Status.ACTIVE
                membership.joined_at = membership.joined_at or timezone.now()
            membership.save(update_fields=["role", "status", "joined_at", "updated_at"])
        return Response(
            {
                "id": target_user.id,
                "username": target_user.get_username(),
                "group_id": group.id,
                "role": membership.role,
            }
        )


class KakaoLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        client_id = os.environ.get("KAKAO_REST_API_KEY") or getattr(
            settings, "KAKAO_REST_API_KEY", ""
        )
        redirect_uri = os.environ.get("KAKAO_REDIRECT_URI") or getattr(
            settings, "KAKAO_REDIRECT_URI", ""
        )
        if not client_id or not redirect_uri:
            return Response(
                {"detail": "Kakao OAuth environment not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        kakao_auth_url = "https://kauth.kakao.com/oauth/authorize?" + urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
            }
        )
        return HttpResponseRedirect(kakao_auth_url)

    def post(self, request):
        code = request.data.get("code")
        if not code:
            raise ValidationError({"code": "code is required"})

        client_id = os.environ.get("KAKAO_REST_API_KEY") or getattr(
            settings, "KAKAO_REST_API_KEY", ""
        )
        redirect_uri = os.environ.get("KAKAO_REDIRECT_URI") or getattr(
            settings, "KAKAO_REDIRECT_URI", ""
        )
        if not client_id or not redirect_uri:
            raise ValidationError({"detail": "Kakao OAuth environment not configured"})

        try:
            token_payload = exchange_code_for_token(
                code,
                client_id=client_id,
                redirect_uri=redirect_uri,
            )
        except KakaoServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        access_token = token_payload.get("access_token")
        if not access_token:
            return Response(
                {"detail": "access_token missing in Kakao response"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            kakao_user = fetch_user_me(access_token)
        except KakaoServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        kakao_id = kakao_user.get("id")
        if kakao_id is None:
            return Response(
                {"detail": "kakao user id not found"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        kakao_account = kakao_user.get("kakao_account") or {}
        email = kakao_account.get("email")
        profile = kakao_account.get("profile") or {}
        nickname = profile.get("nickname")

        User = get_user_model()
        user, _ = User.objects.update_or_create(
            kakao_id=kakao_id,
            defaults={
                "email": email or None,
                "username": f"kakao_{kakao_id}",
                "first_name": nickname or "",
            },
        )
        # Ensure email uniqueness fallback
        if email and user.email != email:
            user.email = email
            user.save(update_fields=["email"])

        refresh = RefreshToken.for_user(user)
        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }
        return Response(data, status=status.HTTP_200_OK)


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": UserSerializer(request.user).data})


class KakaoCallbackAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.query_params.get("code")
        error = request.query_params.get("error")
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
        if not code:
            return Response(
                {"detail": "code is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        client_id = os.environ.get("KAKAO_REST_API_KEY") or getattr(
            settings, "KAKAO_REST_API_KEY", ""
        )
        redirect_uri = os.environ.get("KAKAO_REDIRECT_URI") or getattr(
            settings, "KAKAO_REDIRECT_URI", ""
        )
        if not client_id or not redirect_uri:
            return Response(
                {"detail": "Kakao OAuth environment not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            token_payload = exchange_code_for_token(
                code,
                client_id=client_id,
                redirect_uri=redirect_uri,
            )
        except KakaoServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        access_token = token_payload.get("access_token")
        if not access_token:
            return Response(
                {"detail": "access_token missing in Kakao response"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            kakao_user = fetch_user_me(access_token)
        except KakaoServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        kakao_id = kakao_user.get("id")
        if kakao_id is None:
            return Response(
                {"detail": "kakao user id not found"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        kakao_account = kakao_user.get("kakao_account") or {}
        email = kakao_account.get("email")
        profile = kakao_account.get("profile") or {}
        nickname = profile.get("nickname")

        User = get_user_model()
        user, _ = User.objects.update_or_create(
            kakao_id=kakao_id,
            defaults={
                "email": email or None,
                "username": f"kakao_{kakao_id}",
                "first_name": nickname or "",
            },
        )
        if email and user.email != email:
            user.email = email
            user.save(update_fields=["email"])

        refresh = RefreshToken.for_user(user)

        # 준비된 프런트엔드 리다이렉션 URL
        redirect_base = os.environ.get("KAKAO_LOGIN_REDIRECT_URL") or getattr(
            settings, "KAKAO_LOGIN_REDIRECT_URL", None
        )

        if not redirect_base:
            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": UserSerializer(user).data,
                }
            )

        query_string = urlencode(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )
        redirect_target = f"{redirect_base}?{query_string}"
        return HttpResponseRedirect(redirect_target)
