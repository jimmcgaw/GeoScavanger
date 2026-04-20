from rest_framework import serializers

from apps.audio.models import AudioClip


class PlayHistoryEntrySerializer(serializers.Serializer):
    clip_id = serializers.PrimaryKeyRelatedField(
        queryset=AudioClip.objects.all(),
        source="clip",
    )
    played_at = serializers.DateTimeField()


class HistorySyncSerializer(serializers.Serializer):
    entries = PlayHistoryEntrySerializer(many=True)
