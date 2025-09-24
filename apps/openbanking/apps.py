# moved from apps/common/apps.py
from django.apps import AppConfig


class OpenBankingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.openbanking"
