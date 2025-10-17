from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("groups", "0001_initial"),
        ("openbanking", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="openbankingaccount",
            name="fintech_use_num",
            field=models.CharField(db_index=True, max_length=24),
        ),
        migrations.AddField(
            model_name="openbankingaccount",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="openbanking_accounts",
                to="groups.group",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="openbankingaccount",
            unique_together={("group", "fintech_use_num")},
        ),
    ]
