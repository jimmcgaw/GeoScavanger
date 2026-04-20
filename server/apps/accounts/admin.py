from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("google_sub", "email", "name", "user", "created_at")
    search_fields = ("google_sub", "email", "name")
