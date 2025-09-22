# moved from apps/common/admin.py
from .budget import BudgetAdmin  # noqa: F401
from .dues import PaymentAdmin  # noqa: F401
from .ledger import TransactionAdmin  # noqa: F401
from .openbanking import OpenBankingAccountAdmin  # noqa: F401
