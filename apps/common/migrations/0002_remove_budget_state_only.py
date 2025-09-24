# moved from apps/common/migrations/0001_initial.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0001_initial"),
        ("budget", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="transaction",
                    name="budget",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="transactions",
                        to="budget.Budget",
                    ),
                ),
                migrations.DeleteModel(name="Budget"),
            ],
        ),
    ]
