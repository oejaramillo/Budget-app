"""Production settings: fail fast on missing configuration, stay secure by default."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

DEBUG = False

# The development profile and the committed template both carry placeholder
# secrets. Accepting one of those in production would be worse than a crash, so
# they are rejected explicitly.
_PLACEHOLDER_SECRETS = {
    "",
    "change-me-generate-a-real-secret",
    "django-insecure-development-only-key-change-me",
}

if not SECRET_KEY or SECRET_KEY in _PLACEHOLDER_SECRETS or SECRET_KEY.startswith("dev-only-"):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set to a unique value in production. "
        'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
    )

if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["*"]:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must list your real hostnames in production "
        '(for example "budget-api.onrender.com").'
    )

if not CORS_ALLOWED_ORIGINS and not CORS_ALLOW_ALL_ORIGINS:
    raise ImproperlyConfigured(
        "Set CORS_ALLOWED_ORIGINS to the origins that may call this API, "
        'for example "https://budget.example.com".'
    )

if not DATABASE_CONFIGURED:
    raise ImproperlyConfigured(
        "No PostgreSQL database configured. Set DATABASE_URL (Neon) or the DB_* "
        "variables; the SQLite fallback is development-only."
    )

# --- Transport security -----------------------------------------------------
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Reuse database connections (Neon pooler endpoint handles the rest).
DATABASES["default"].setdefault("CONN_MAX_AGE", 60)
DATABASES["default"].setdefault("CONN_HEALTH_CHECKS", True)

# --- Static files -----------------------------------------------------------
# Only needed when Django itself serves the built React bundle.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# --- Logging ----------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
