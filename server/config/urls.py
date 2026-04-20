"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/v1/",
        include(
            [
                path("auth/", include("apps.accounts.urls")),
                path("clips/", include("apps.audio.urls")),
                path("history/", include("apps.history.urls")),
            ]
        ),
    ),
]
