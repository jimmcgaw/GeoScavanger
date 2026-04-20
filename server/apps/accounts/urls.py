from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import GoogleAuthView

urlpatterns = [
    path("google/", GoogleAuthView.as_view(), name="auth-google"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
]
