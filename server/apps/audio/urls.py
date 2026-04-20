from django.urls import path

from .views import NearbyClipsView

urlpatterns = [
    path("nearby/", NearbyClipsView.as_view(), name="clips-nearby"),
]
