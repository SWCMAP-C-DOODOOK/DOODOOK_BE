from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("groups", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="group",
            name="invite_code",
            field=models.CharField(
                blank=True,
                help_text="6-character alphanumeric invite code",
                max_length=16,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="group",
            name="invite_code_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
