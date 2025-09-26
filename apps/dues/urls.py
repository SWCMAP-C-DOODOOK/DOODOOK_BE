from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.dues.views import DuesReminderViewSet, PaymentExportView, PaymentTotalsView

router = DefaultRouter()
router.register(r"dues/reminders", DuesReminderViewSet, basename="dues-reminder")

urlpatterns = [
    path("dues/totals", PaymentTotalsView.as_view()),
    path("dues/export", PaymentExportView.as_view()),
]

urlpatterns += router.urls
