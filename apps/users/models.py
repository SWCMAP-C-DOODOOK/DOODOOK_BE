from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.models import TimeStampedModel


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", "admin"
        MEMBER = "member", "member"

    email = models.EmailField(unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    kakao_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    role = models.CharField(
        max_length=10, choices=Roles.choices, default=Roles.MEMBER, db_index=True
    )

    def __str__(self):
        return f"{self.username} ({self.email})" if self.email else self.username


# migration 필요


def user_avatar_upload_to(instance, filename: str) -> str:
    return f"users/{instance.user_id}/avatars/{filename}"


class UserProfile(TimeStampedModel):
    """
    사용자 프로필 정보. 기본 User(장고 기본 auth_user)에 1:1 확장.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    nickname = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    kakao_id = models.CharField(
        max_length=64, blank=True, help_text="Kakao user id (optional)"
    )
    avatar = models.ImageField(upload_to=user_avatar_upload_to, blank=True, null=True)

    def __str__(self):
        return f"Profile<{self.user_id}:{self.nickname or self.user.username}>"


# migration 필요
