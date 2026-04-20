from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.gis.db import models

if TYPE_CHECKING:
    from apps.audio.models import AudioClip


class AudioClipManager(models.Manager["AudioClip"]):
    def get_nearby_clips(
        self,
        lat: float,
        lng: float,
        limit: int = 5,
        exclude_ids: list[int] | None = None,
    ) -> list[AudioClip]:
        """
        Return up to ``limit`` nearby clips for ``(lat, lng)``, excluding ``exclude_ids``.

        PostGIS query implementation is deferred.
        """
        raise NotImplementedError
