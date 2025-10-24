# policies/views.py (상단)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
# 🌟 이 줄을 추가합니다.
from rest_framework.permissions import AllowAny 
from .models import Policy
from .serializers import PolicySerializer 
# ...

class CurrentPolicyView(APIView):
    # 🌟 이 한 줄을 추가하여 로그인 없이 접근 가능하게 만듭니다. 🌟
    permission_classes = [AllowAny]
    def get(self, request):
        # URL 쿼리 파라미터에서 'type' 값을 가져옵니다. (예: 'privacy', 'terms')
        policy_type = request.query_params.get('type')
        
        # 'type' 파라미터가 없는 경우 처리
        if not policy_type:
            return Response({"error": "policy_type 쿼리 파라미터가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 해당 유형 중 'is_active=True'인 정책(최신 활성화 버전)을 조회합니다.
            policy_instance = Policy.objects.get(policy_type=policy_type, is_active=True)
            
            # Serializer를 사용하여 조회된 데이터를 JSON으로 변환합니다.
            serializer = PolicySerializer(policy_instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Policy.DoesNotExist:
            # DB에 해당 유형의 활성화된 정책이 없는 경우 404 에러를 반환합니다.
            return Response({"error": f"활성화된 정책({policy_type})을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)