# policies/serializers.py

from rest_framework import serializers
from .models import Policy

class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        # 프론트엔드에 필요한 필드만 노출합니다.
        fields = ['title', 'content_md', 'effective_date', 'version']