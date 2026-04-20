from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Application profile keyed to a Google subject (`sub`)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    google_sub = models.CharField(max_length=255, unique=True, db_index=True)
    email = models.EmailField(blank=True)
    name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.google_sub
