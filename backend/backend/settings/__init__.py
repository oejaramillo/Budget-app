"""
Settings package entry point.

`manage.py` and the WSGI/ASGI modules point at `backend.settings`, which defaults
to the development profile. Select another profile explicitly:

    DJANGO_SETTINGS_MODULE=backend.settings.production gunicorn backend.wsgi
"""

import os

_profile = os.environ.get("DJANGO_ENV", "development").lower()

if _profile in {"production", "prod"}:
    from .production import *  # noqa: F401,F403
else:
    from .development import *  # noqa: F401,F403
