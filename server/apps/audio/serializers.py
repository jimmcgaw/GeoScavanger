import json

from rest_framework import serializers

from .models import AudioClip


class NearbyClipsRequestSerializer(serializers.Serializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    limit = serializers.IntegerField(required=False, default=5, min_value=1, max_value=20)
    exclude_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )


class AudioClipSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    geofence = serializers.SerializerMethodField()

    class Meta:
        model = AudioClip
        fields = (
            "id",
            "title",
            "description",
            "cdn_uri",
            "duration_seconds",
            "location",
            "radius_meters",
            "geofence",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_location(self, obj: AudioClip) -> dict | None:
        if obj.location is None:
            return None
        return json.loads(obj.location.json)

    def get_geofence(self, obj: AudioClip) -> dict | None:
        if obj.geofence is None:
            return None
        return json.loads(obj.geofence.json)
