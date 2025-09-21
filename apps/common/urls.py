from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BudgetViewSet,
    DuesStatusView,
    DuesUnpaidView,
    OpenBankingAccountViewSet,
    OpenBankingBalanceView,
    OpenBankingTransactionsView,
    PaymentViewSet,
    ReceiptOCRView,
    TransactionViewSet,
)


router = DefaultRouter()
router.register(r"budgets", BudgetViewSet, basename="budget")
router.register(r"dues/payments", PaymentViewSet, basename="payment")
router.register(r"transactions", TransactionViewSet, basename="transaction")
router.register(r"openbanking/accounts", OpenBankingAccountViewSet, basename="ob-accounts")

urlpatterns = [
    path("dues/status", DuesStatusView.as_view()),
    path("dues/unpaid", DuesUnpaidView.as_view()),
    path("ocr/receipt", ReceiptOCRView.as_view()),
    path("openbanking/balance", OpenBankingBalanceView.as_view()),
    path("openbanking/transactions", OpenBankingTransactionsView.as_view()),
]

urlpatterns += router.urls
