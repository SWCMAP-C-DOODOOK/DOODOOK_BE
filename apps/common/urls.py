from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.common.views.budget import BudgetViewSet
from apps.common.views.dues import DuesStatusView, DuesUnpaidView, PaymentViewSet
from apps.common.views.ledger import TransactionViewSet
from apps.common.views.ocr import ReceiptOCRView
from apps.common.views.openbanking import (
    OpenBankingAccountViewSet,
    OpenBankingBalanceView,
    OpenBankingTransactionsView,
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
