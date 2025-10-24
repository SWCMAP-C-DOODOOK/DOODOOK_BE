# policies/apps.py (수정 후)

from django.apps import AppConfig

class PoliciesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.policies' # 👈 settings.py의 경로와 일치시킵니다.
    verbose_name = '정책 관리' # (선택 사항) 관리자 페이지에 표시될 이름