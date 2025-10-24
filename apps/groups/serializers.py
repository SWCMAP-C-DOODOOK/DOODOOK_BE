from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from apps.groups.models import Group, GroupMembership
from apps.groups.services import generate_invite_code

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
        self._ensure_invite_code(group)
        GroupMembership.objects.create(
            group=group,
            user=request.user,
            role=GroupMembership.Roles.ADMIN,
            status=GroupMembership.Status.ACTIVE,
            invited_by=request.user,
            joined_at=timezone.now(),
        )
        return group

    def _ensure_invite_code(self, group: Group) -> None:
        if group.invite_code:
            return
        for _ in range(10):
            candidate = generate_invite_code()
            if not Group.objects.filter(invite_code=candidate).exists():
                group.invite_code = candidate
                group.save(update_fields=["invite_code", "updated_at"])
                return
        raise serializers.ValidationError({"detail": "초대 코드를 생성할 수 없습니다. 다시 시도해주세요."})


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


class GroupJoinSerializer(serializers.Serializer):
    invite_code = serializers.CharField(max_length=16)

    def validate_invite_code(self, value: str) -> str:
        code = (value or "").strip().upper()
        if len(code) != 6 or not code.isalnum():
            raise serializers.ValidationError("초대 코드는 6자리 영문/숫자 조합이어야 합니다.")
        try:
            group = Group.objects.get(invite_code=code)
        except Group.DoesNotExist as exc:
            raise serializers.ValidationError("유효하지 않은 초대 코드입니다.") from exc
        expires_at = group.invite_code_expires_at
        if expires_at and expires_at < timezone.now():
            raise serializers.ValidationError("초대 코드가 만료되었습니다.")
        self.context["group"] = group
        return code

    def create(self, validated_data):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError({"detail": "인증이 필요합니다."})
        group: Group = self.context["group"]
        membership, created = GroupMembership.objects.get_or_create(
            group=group,
            user=request.user,
            defaults={
                "role": GroupMembership.Roles.MEMBER,
                "status": GroupMembership.Status.ACTIVE,
                "joined_at": timezone.now(),
            },
        )
        updates: list[str] = []
        if membership.status != GroupMembership.Status.ACTIVE:
            membership.status = GroupMembership.Status.ACTIVE
            updates.append("status")
        if membership.joined_at is None:
            membership.joined_at = timezone.now()
            updates.append("joined_at")
        if membership.left_at is not None:
            membership.left_at = None
            updates.append("left_at")
        if updates:
            updates.append("updated_at")
            membership.save(update_fields=list(set(updates)))
        self.instance = membership
        self._created = created
        return membership
