from django.conf import settings
from django.db import models


class PlayHistoryEntry(models.Model):
    """A single play event for a clip by a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="play_history_entries",
    )
    clip = models.ForeignKey(
        "audio.AudioClip",
        on_delete=models.CASCADE,
        related_name="play_history_entries",
    )
    played_at = models.DateTimeField()

    class Meta:
        ordering = ["-played_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "clip", "played_at"],
                name="history_playentry_user_clip_playedat_uniq",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.clip_id}@{self.played_at.isoformat()}"
