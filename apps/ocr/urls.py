# moved from apps/common/urls.py
from django.urls import path

from apps.ocr.views import ReceiptOCRView


urlpatterns = [
    path("ocr/receipt", ReceiptOCRView.as_view()),
]
