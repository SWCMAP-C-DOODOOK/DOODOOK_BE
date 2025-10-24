# moved from apps/common/urls.py
from django.urls import path

from apps.ocr.views import (
    OcrApprovalDetailView,
    OcrPendingApprovalListView,
    OcrValidationLogListView,
    OcrApproveView,
    OcrRejectView,
    ReceiptOCRView,
)

urlpatterns = [
    path("ocr/receipt", ReceiptOCRView.as_view()),
    path("ocr/approvals/pending", OcrPendingApprovalListView.as_view()),
    path("ocr/transactions/<int:pk>/approval", OcrApprovalDetailView.as_view()),
    path("ocr/transactions/<int:pk>/logs", OcrValidationLogListView.as_view()),
    path("ocr/transactions/<int:pk>/approve", OcrApproveView.as_view()),
    path("ocr/transactions/<int:pk>/reject", OcrRejectView.as_view()),
]
