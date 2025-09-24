# moved from apps/common/migrations/0001_initial.py
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Budget",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("name", models.CharField(max_length=50)),
                        ("allocated_amount", models.PositiveIntegerField()),
                        ("description", models.CharField(blank=True, max_length=255, null=True)),
                    ],
                    options={
                        "db_table": "common_budget",
                        "ordering": ["name"],
                    },
                ),
            ],
        ),
    ]
