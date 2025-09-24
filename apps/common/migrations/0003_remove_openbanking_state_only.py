# moved from apps/common/migrations/0001_initial.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0002_remove_budget_state_only"),
        ("openbanking", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="OpenBankingAccount"),
            ],
        ),
    ]
