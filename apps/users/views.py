import os
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsAdminRole

from .models import UserProfile
from .serializers import RoleUpdateSerializer, UserProfileSerializer


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.select_related('user').all()
    serializer_class = UserProfileSerializer

    def perform_create(self, serializer):
        # Admin-only create; attach a user explicitly if provided, otherwise default to request.user
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)

    @action(detail=False, methods=['get'], url_path='kakao/login')
    def kakao_login(self, request):
        """
        Kakao OAuth 2.0 로그인 URL 제공 (리다이렉트는 FE 처리)
        환경변수: KAKAO_CLIENT_ID, KAKAO_REDIRECT_URI
        """
        client_id = os.environ.get('KAKAO_CLIENT_ID', '')
        redirect_uri = os.environ.get('KAKAO_REDIRECT_URI', '')
        kakao_auth_url = "https://kauth.kakao.com/oauth/authorize?" + urlencode({
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
        })
        return Response({'auth_url': kakao_auth_url})

    @action(detail=False, methods=['get'], url_path='kakao/callback')
    def kakao_callback(self, request):
        """
        Kakao 인가코드 수신 콜백 (토큰 교환/유저정보 요청은 추후 구현)
        """
        code = request.query_params.get('code')
        if not code:
            return Response({'detail': 'code is required'}, status=400)
        # TODO: 교환/검증 로직 구현 (requests로 토큰 교환 및 사용자 정보 획득)
        return Response({'received_code': code})


class UserRoleUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def patch(self, request, pk):
        user_model = get_user_model()
        target_user = get_object_or_404(user_model, pk=pk)
        serializer = RoleUpdateSerializer(instance=target_user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if "role" not in serializer.validated_data:
            raise ValidationError({"role": "Role value is required"})
        serializer.save()
        # TODO: enforce additional policies (e.g., prevent self-demotion) if required
        # TODO: audit log for role changes (who changed when)
        return Response({
            "id": target_user.id,
            "username": target_user.get_username(),
            "role": target_user.role,
        })
