from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import AudioClip


@admin.register(AudioClip)
class AudioClipAdmin(GISModelAdmin):
    list_display = ("title", "cdn_uri", "created_at")
