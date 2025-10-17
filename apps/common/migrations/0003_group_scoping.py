from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("groups", "0001_initial"),
        ("common", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payments",
                to="groups.group",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="payment",
            unique_together={("group", "user", "year", "month")},
        ),
        migrations.RemoveIndex(
            model_name="payment",
            name="idx_payment_user_year_month",
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(
                fields=["group", "user", "year", "month"],
                name="idx_pay_group_user_ym",
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="transactions",
                to="groups.group",
            ),
        ),
        migrations.RemoveIndex(
            model_name="transaction",
            name="idx_transaction_date",
        ),
        migrations.RemoveIndex(
            model_name="transaction",
            name="idx_transaction_type_date",
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(
                fields=["group", "date"],
                name="idx_tx_group_date",
            ),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(
                fields=["group", "type", "date"],
                name="idx_tx_group_type_date",
            ),
        ),
    ]
