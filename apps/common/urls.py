from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.common.views.dues import DuesStatusView, DuesUnpaidView, PaymentViewSet
from apps.common.views.ledger import TransactionViewSet
from apps.ocr.views import ReceiptOCRView


router = DefaultRouter()
router.register(r"dues/payments", PaymentViewSet, basename="payment")
router.register(r"transactions", TransactionViewSet, basename="transaction")

urlpatterns = [
    path("dues/status", DuesStatusView.as_view()),
    path("dues/unpaid", DuesUnpaidView.as_view()),
    path("ocr/receipt", ReceiptOCRView.as_view()),
]

urlpatterns += router.urls
