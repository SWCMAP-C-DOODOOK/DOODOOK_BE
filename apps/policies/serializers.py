# policies/serializers.py

from rest_framework import serializers
# from .models import Policy
from .models import PolicyVersion 

class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyVersion
        # 🚨 Policy 대신 PolicyVersion을 사용합니다.
        # 프론트엔드에 필요한 필드만 노출합니다.
        fields = ['title', 'content_md', 'effective_date', 'version']


        # policies/serializers.py (수정할 부분)