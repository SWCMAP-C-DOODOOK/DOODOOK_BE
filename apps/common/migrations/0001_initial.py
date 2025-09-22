from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
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
        migrations.CreateModel(
            name="OpenBankingAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("alias", models.CharField(max_length=50)),
                ("fintech_use_num", models.CharField(db_index=True, max_length=24, unique=True)),
                ("bank_name", models.CharField(blank=True, max_length=50, null=True)),
                ("account_masked", models.CharField(blank=True, max_length=64, null=True)),
                ("enabled", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "common_openbankingaccount",
                "ordering": ["alias"],
            },
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("year", models.PositiveSmallIntegerField()),
                ("month", models.PositiveSmallIntegerField()),
                ("is_paid", models.BooleanField(default=True)),
                ("amount", models.PositiveIntegerField(blank=True, null=True)),
                ("paid_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=models.CASCADE, related_name="payments", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "db_table": "common_payment",
                "ordering": ["-year", "-month", "user"],
            },
        ),
        migrations.CreateModel(
            name="Transaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("amount", models.PositiveIntegerField()),
                ("description", models.CharField(max_length=255)),
                ("date", models.DateField()),
                ("type", models.CharField(choices=[("income", "income"), ("expense", "expense")], max_length=10)),
                ("category", models.CharField(blank=True, max_length=50, null=True)),
                ("receipt_image", models.ImageField(blank=True, null=True, upload_to="receipts/")),
                ("ocr_text", models.TextField(blank=True, null=True)),
                (
                    "budget",
                    models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="transactions", to="common.budget"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=models.CASCADE, related_name="transactions", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "db_table": "common_transaction",
                "ordering": ["-date", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.UniqueConstraint(fields=("user", "year", "month"), name="unique_user_year_month_payment"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["user", "year", "month"], name="idx_payment_user_year_month"),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["date"], name="idx_transaction_date"),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["type", "date"], name="idx_transaction_type_date"),
        ),
    ]
