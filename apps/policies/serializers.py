# policies/serializers.py (최종 깔끔한 버전)

from rest_framework import serializers
from .models import PolicyVersion, UserAgreement 
from .models import UserAgreement # 중복 방지를 위해 삭제합니다.

# 정책 유형 선택지 (모든 Serializer에서 공통으로 사용)
POLICY_TYPES = [
    ('privacy', '개인정보 처리방침'), 
    ('terms', '서비스 약관'), 
    ('youth', '청소년 보호정책'), 
    ('about', '회사 소개')
]


# 1. 문서 조회용 Serializer (GET API 출력)
class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyVersion
        fields = ['title', 'content_md', 'effective_date', 'version']


# 2. 동의 입력용 Serializer (POST API 입력 유효성 검사)
class AgreementInputSerializer(serializers.Serializer):
    # 위에서 정의한 POLICY_TYPES를 사용합니다.
    policy_types = serializers.ListField(
        child=serializers.ChoiceField(choices=POLICY_TYPES, allow_blank=False),
        min_length=1,
    )


# 3. 동의 기록 출력용 Serializer (POST API 출력)
class UserAgreementSerializer(serializers.ModelSerializer):
    # 정책 버전 정보를 커스텀 포맷으로 출력
    policy_version_info = serializers.SerializerMethodField() 

    class Meta:
        model = UserAgreement
        # 사용자에게 기록된 정보를 반환
        fields = ('id', 'policy_version_info', 'agreed_at')
        read_only_fields = ('user', 'policy_version', 'agreed_at') 

    def get_policy_version_info(self, obj):
        # 'privacy (v2.1)' 형태로 반환하는 로직
        return f"{obj.policy_version.policy_type} (v{obj.policy_version.version})"