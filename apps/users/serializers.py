from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import UserProfile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]
        read_only_fields = ["id", "username", "email", "role"]


class UserProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(use_url=True, required=False, allow_null=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "user",
            "nickname",
            "phone",
            "kakao_id",
            "avatar",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class RoleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["role"]
