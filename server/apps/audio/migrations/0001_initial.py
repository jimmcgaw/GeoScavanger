import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AudioClip",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("cdn_uri", models.URLField(max_length=2048)),
                ("duration_seconds", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "location",
                    django.contrib.gis.db.models.fields.PointField(
                        blank=True,
                        geography=True,
                        null=True,
                        srid=4326,
                    ),
                ),
                ("radius_meters", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "geofence",
                    django.contrib.gis.db.models.fields.PolygonField(
                        blank=True,
                        geography=True,
                        null=True,
                        srid=4326,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
