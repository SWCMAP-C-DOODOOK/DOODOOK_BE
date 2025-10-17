from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.groups.models import GroupMembership

from .models import UserProfile

User = get_user_model()


class GroupMembershipSerializer(serializers.ModelSerializer):
    group_id = serializers.IntegerField(source="group_id", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = GroupMembership
        fields = ["group_id", "group_name", "role", "status", "is_admin"]

    def get_is_admin(self, obj: GroupMembership) -> bool:
        return obj.role == GroupMembership.Roles.ADMIN


class UserSerializer(serializers.ModelSerializer):
    memberships = serializers.SerializerMethodField()
    is_admin_any = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone_number",
            "is_admin_any",
            "memberships",
        ]
        read_only_fields = ["id", "username", "email", "phone_number", "is_admin_any"]

    def get_memberships(self, obj: User):
        memberships = obj.group_memberships.select_related("group").all()
        return GroupMembershipSerializer(memberships, many=True).data

    def get_is_admin_any(self, obj: User) -> bool:
        return obj.group_memberships.filter(
            status=GroupMembership.Status.ACTIVE,
            role=GroupMembership.Roles.ADMIN,
        ).exists() or obj.is_staff or obj.is_superuser


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


class RoleUpdateSerializer(serializers.Serializer):
    group_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=GroupMembership.Roles.choices)
