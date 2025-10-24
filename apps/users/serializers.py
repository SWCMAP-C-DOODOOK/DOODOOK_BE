from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.groups.models import GroupMembership

from .models import UserProfile

User = get_user_model()


class GroupMembershipSerializer(serializers.ModelSerializer):
    group_id = serializers.IntegerField(read_only=True)
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
    first_name = serializers.CharField(
        source="user.first_name", required=False, allow_blank=True
    )

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "user",
            "first_name",
            "nickname",
            "phone",
            "kakao_id",
            "avatar",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def create(self, validated_data):
        user_data = validated_data.pop("user", {})
        profile = super().create(validated_data)
        first_name = user_data.get("first_name")
        if first_name is not None and profile.user.first_name != first_name:
            profile.user.first_name = first_name
            profile.user.save(update_fields=["first_name"])
        return profile

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        profile = super().update(instance, validated_data)
        first_name = user_data.get("first_name")
        if first_name is not None and profile.user.first_name != first_name:
            profile.user.first_name = first_name
            profile.user.save(update_fields=["first_name"])
        return profile


class RoleUpdateSerializer(serializers.Serializer):
    group_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=GroupMembership.Roles.choices)
