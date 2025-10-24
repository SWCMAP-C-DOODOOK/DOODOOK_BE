# policies/urls.py

from django.urls import path
from .views import CurrentPolicyView # 2단계에서 만든 View import

urlpatterns = [
    # 이 경로는 메인 config/urls.py에 연결되어 최종적으로 /api/v1/policy 가 됩니다.
    path('policy', CurrentPolicyView.as_view(), name='current-policy-api'),
]