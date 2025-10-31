from django.db import models
# User 모델 경로 확인 후 import
from apps.users.models import User 

# 🌟 새로운 PolicyVersion 모델 (문서 전문 및 버전 기록)
class PolicyVersion(models.Model):
    POLICY_CHOICES = [
        ('privacy', '개인정보 처리방침'),
        ('terms', '서비스 약관'),
        ('youth', '청소년 보호정책'),
        ('about', '회사 소개'),
    ]
    
    # version 필드는 unique=True 대신 Meta의 unique_together로 관리합니다.
    # 🌟 이 title 필드가 누락되어 오류가 발생했습니다. 다시 추가합니다. 🌟
    title = models.CharField(max_length=255, verbose_name='정책 제목')
    policy_type = models.CharField(max_length=50, choices=POLICY_CHOICES, verbose_name='정책 유형')
    version = models.CharField(max_length=50, verbose_name='버전') # unique=True 제거
    content_md = models.TextField(verbose_name='마크다운 본문') 
    effective_date = models.DateField(verbose_name='시행일')
    is_active = models.BooleanField(default=False, verbose_name='현재 활성화 여부') 
    
    class Meta:
        # 🚨 1. PolicyVersion에 Meta 추가: 정책 유형별로 버전이 고유해야 함.
        unique_together = ('policy_type', 'version')
        verbose_name = '정책 버전'
        verbose_name_plural = '정책 버전'

    def __str__(self):
        return f"[{self.policy_type}] {self.version}"
    
# 🌟 새로운 UserAgreement 모델 (사용자 동의 이력 기록)
class UserAgreement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자')
    policy_version = models.ForeignKey(PolicyVersion, on_delete=models.PROTECT, verbose_name='동의한 정책 버전')
    agreed_at = models.DateTimeField(auto_now_add=True, verbose_name='동의 시점')

    class Meta:
        # 🚨 2. UserAgreement의 unique_together 수정 (user와 policy_version FK를 묶음)
        unique_together = ('user', 'policy_version') 
        verbose_name = '사용자 동의 이력'
        verbose_name_plural = '사용자 동의 이력'