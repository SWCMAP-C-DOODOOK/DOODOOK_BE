from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("groups", "0001_initial"),
        ("dues", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="duesreminder",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="dues_reminders",
                to="groups.group",
            ),
        ),
    ]
