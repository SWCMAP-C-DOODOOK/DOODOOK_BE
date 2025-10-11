# moved from apps/common/admin.py
from apps.budget.admin import BudgetAdmin  # noqa: F401
from apps.openbanking.admin import OpenBankingAccountAdmin  # noqa: F401

from .dues import PaymentAdmin  # noqa: F401
from .ledger import TransactionAdmin  # noqa: F401
