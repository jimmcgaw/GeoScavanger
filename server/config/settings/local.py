"""Local development settings."""

from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = env.list(  # noqa: F405
    "ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "0.0.0.0", "web"],
)

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
