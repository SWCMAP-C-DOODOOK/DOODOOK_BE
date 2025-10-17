from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("groups", "0001_initial"),
        ("budget", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="budget",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="budgets",
                to="groups.group",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="budget",
            unique_together={("group", "name")},
        ),
    ]
