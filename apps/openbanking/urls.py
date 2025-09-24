# moved from apps/common/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.openbanking.views import (
    OpenBankingAccountViewSet,
    OpenBankingBalanceView,
    OpenBankingTransactionsView,
)


router = DefaultRouter()
router.register(r"openbanking/accounts", OpenBankingAccountViewSet, basename="ob-accounts")

urlpatterns = [
    path("openbanking/balance", OpenBankingBalanceView.as_view()),
    path("openbanking/transactions", OpenBankingTransactionsView.as_view()),
]

urlpatterns += router.urls
