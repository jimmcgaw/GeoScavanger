from django.urls import path

from .views import HistorySyncView

urlpatterns = [
    path("sync/", HistorySyncView.as_view(), name="history-sync"),
]
