# policies/admin.py

from django.contrib import admin
# from .models import Policy
# 🚨 Policy 대신 PolicyVersion과 UserAgreement를 import합니다.
from .models import PolicyVersion, UserAgreement

# @admin.register(Policy)
# class PolicyAdmin(admin.ModelAdmin):
#     # (생략)
#     list_display = ('policy_type', 'title', 'version', 'is_active', 'effective_date', 'updated_at')
#     # (생략)
#     list_editable = ('is_active',)
@admin.register(PolicyVersion)
class PolicyVersionAdmin(admin.ModelAdmin):
    # list_display, list_filter 등은 PolicyVersion 모델의 필드를 참조하도록 수정합니다.
    list_display = ('policy_type', 'version', 'is_active', 'effective_date')
    list_filter = ('is_active', 'policy_type')
    search_fields = ('content_md',)

# 🌟 UserAgreement 모델도 관리자 페이지에 등록 
@admin.register(UserAgreement)
class UserAgreementAdmin(admin.ModelAdmin):
    list_display = ('user', 'policy_version', 'agreed_at')
    list_filter = ('policy_version',)
    search_fields = ('user__username',) # 사용자 이름으로 검색 가능