from django.db import models

class Policy(models.Model):
    # 정책의 유형 (privacy, terms, youth, about)을 구분하는 옵션 정의
    POLICY_CHOICES = [
        ('privacy', '개인정보 처리방침'),
        ('terms', '서비스 약관'),
        ('youth', '청소년 보호정책'),
        ('about', '회사 소개'),
    ]
    
    # 정책 유형 (예: 'privacy'). 중복 방지를 위해 unique=True 설정
    policy_type = models.CharField(
        max_length=50, 
        choices=POLICY_CHOICES, 
        unique=True, 
        verbose_name='정책 유형'
    )
    
    # 정책 제목
    title = models.CharField(max_length=255, verbose_name='정책 제목')
    
    # 마크다운 본문: 긴 텍스트를 저장하기 위해 TextField 사용
    content_md = models.TextField(verbose_name='마크다운 본문') 
    
    # 활성화 상태: 현재 사용자에게 보여줄 정책인지
    is_active = models.BooleanField(default=False, verbose_name='활성화 여부')
    
    # 정책 버전 (예: 1.0, 2.1)
    version = models.CharField(max_length=50, verbose_name='버전')

    effective_date = models.DateField(verbose_name='시행일')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # 관리자 페이지에서 항목을 구분하기 쉽게 하기 위한 설정
        return f"[{self.policy_type}] {self.title}"