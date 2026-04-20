from django.contrib import admin

from .models import PlayHistoryEntry


@admin.register(PlayHistoryEntry)
class PlayHistoryEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "clip", "played_at")
    list_filter = ("played_at",)
