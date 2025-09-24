# moved to apps/common/admin package
from apps.budget.admin import BudgetAdmin
from apps.openbanking.admin import OpenBankingAccountAdmin
from .admin import PaymentAdmin, TransactionAdmin

__all__ = [
    "BudgetAdmin",
    "OpenBankingAccountAdmin",
    "PaymentAdmin",
    "TransactionAdmin",
]
