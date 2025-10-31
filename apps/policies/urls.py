from django.urls import path
from .views import CurrentPolicyView, AgreePolicyView

urlpatterns = [
    # GET /api/policy?type={privacy}: 최신 정책 문서 조회
    path('policy', CurrentPolicyView.as_view(), name='policy-content'),
    
    # POST /api/policy/agree: 사용자 동의 이력 기록 (법적 필수 기능)
    path('policy/agree', AgreePolicyView.as_view(), name='policy-agree'),
]