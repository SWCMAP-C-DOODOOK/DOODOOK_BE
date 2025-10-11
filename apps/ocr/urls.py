# moved from apps/common/urls.py
from django.urls import path

from apps.ocr.views import OcrApproveView, OcrRejectView, ReceiptOCRView

urlpatterns = [
    path("ocr/receipt", ReceiptOCRView.as_view()),
    path("ocr/transactions/<int:pk>/approve", OcrApproveView.as_view()),
    path("ocr/transactions/<int:pk>/reject", OcrRejectView.as_view()),
]
