from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from apps.groups.models import Group, GroupMembership

User = get_user_model()


class GroupSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Group
        fields = [
            "id",
            "name",
            "description",
            "owner",
            "role",
            "member_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "role", "member_count", "created_at", "updated_at"]

    def get_role(self, obj: Group):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        membership = obj.memberships.filter(
            user=request.user, status=GroupMembership.Status.ACTIVE
        ).first()
        return getattr(membership, "role", None)

    def get_member_count(self, obj: Group) -> int:
        return obj.memberships.filter(status=GroupMembership.Status.ACTIVE).count()


class GroupCreateSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Group
        fields = ["id", "name", "description", "owner", "created_at", "updated_at"]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError({"detail": "인증된 사용자만 그룹을 생성할 수 있습니다."})
        group = Group.objects.create(owner=request.user, **validated_data)
        GroupMembership.objects.create(
            group=group,
            user=request.user,
            role=GroupMembership.Roles.ADMIN,
            status=GroupMembership.Status.ACTIVE,
            invited_by=request.user,
            joined_at=timezone.now(),
        )
        return group


class GroupMembershipSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = GroupMembership
        fields = [
            "id",
            "group_id",
            "user",
            "role",
            "role_display",
            "status",
            "status_display",
            "joined_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_user(self, obj: GroupMembership):
        user = obj.user
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone_number": getattr(user, "phone_number", None),
        }


class GroupMembershipMutationSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    role = serializers.ChoiceField(choices=GroupMembership.Roles.choices, required=False)
    status = serializers.ChoiceField(
        choices=GroupMembership.Status.choices,
        required=False,
    )

    def validate(self, attrs):
        data = super().validate(attrs)
        if self.instance is None and "user_id" not in data:
            raise serializers.ValidationError({"user_id": "user_id is required"})
        return data
