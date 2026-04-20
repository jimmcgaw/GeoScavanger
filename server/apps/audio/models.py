from django.contrib.gis.db import models
from django.core.exceptions import ValidationError

from .managers import AudioClipManager


class AudioClip(models.Model):
    """Geotagged audio clip metadata (audio served from CDN)."""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cdn_uri = models.URLField(max_length=2048)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    location = models.PointField(geography=True, srid=4326, null=True, blank=True)
    radius_meters = models.PositiveIntegerField(null=True, blank=True)
    geofence = models.PolygonField(geography=True, srid=4326, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AudioClipManager()

    class Meta:
        ordering = ["-created_at"]

    def clean(self) -> None:
        has_point = self.location is not None and self.radius_meters is not None
        has_geofence = self.geofence is not None
        partial_point = (self.location is not None) ^ (self.radius_meters is not None)

        if partial_point:
            raise ValidationError(
                "Point clips require both location and radius_meters, or neither."
            )
        if has_point and has_geofence:
            raise ValidationError("Cannot set both a point radius and a geofence.")
        if not has_point and not has_geofence:
            raise ValidationError("Must set either (location + radius_meters) or geofence.")

    def __str__(self) -> str:
        return self.title
