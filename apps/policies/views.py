from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated # AllowAny와 IsAuthenticated 사용
from django.db import transaction 

# 🚨 두 모델과 Serializer를 깔끔하게 import
from .models import PolicyVersion, UserAgreement 
from .serializers import PolicySerializer, AgreementInputSerializer, UserAgreementSerializer 


class CurrentPolicyView(APIView):
    # 로그인 없이 접근 가능 (모두가 약관을 볼 수 있도록)
    permission_classes = [AllowAny] 
    
    def get(self, request):
        policy_type = request.query_params.get('type')
        
        if not policy_type:
            return Response({"error": "policy_type 쿼리 파라미터가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 최신 활성화된 정책 버전 조회
            policy_instance = PolicyVersion.objects.get(policy_type=policy_type, is_active=True)
            
            serializer = PolicySerializer(policy_instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except PolicyVersion.DoesNotExist:
            return Response({"error": f"활성화된 정책({policy_type})을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)


class AgreePolicyView(APIView):
    # 동의 기록은 사용자 ID가 필요하므로 로그인 필수
    permission_classes = [IsAuthenticated] 

    @transaction.atomic
    def post(self, request):
        serializer = AgreementInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user 
        policy_types = serializer.validated_data['policy_types']
        agreements = []
        
        for p_type in policy_types:
            # 현재 활성화된 정책 버전 찾기
            try:
                active_version = PolicyVersion.objects.get(policy_type=p_type, is_active=True)
            except PolicyVersion.DoesNotExist:
                # 활성화된 정책이 없으면 오류 반환 (트랜잭션 Rollback)
                return Response(
                    {"error": f"활성화된 {p_type} 정책을 찾을 수 없습니다. 관리자에게 문의하세요."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # UserAgreement 테이블에 동의 이력 기록 (Commit 대기)
            agreement, created = UserAgreement.objects.get_or_create(
                user=user,
                policy_version=active_version,
            )
            agreements.append(agreement)

        # 성공 응답 반환 (트랜잭션 Commit)
        response_serializer = UserAgreementSerializer(agreements, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)