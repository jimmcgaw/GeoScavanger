from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("audio", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlayHistoryEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("played_at", models.DateTimeField()),
                (
                    "clip",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="play_history_entries",
                        to="audio.audioclip",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="play_history_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-played_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="playhistoryentry",
            constraint=models.UniqueConstraint(
                fields=("user", "clip", "played_at"),
                name="history_playentry_user_clip_playedat_uniq",
            ),
        ),
    ]
