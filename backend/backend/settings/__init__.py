"""
Settings package entry point.

`manage.py` and the WSGI/ASGI modules point at `backend.settings`, which defaults to
the development profile. Select another profile explicitly:

    DJANGO_ENV=production DJANGO_SETTINGS_MODULE=backend.settings gunicorn backend.wsgi

The `test` profile is selected automatically while the test suite runs, so
`manage.py test` never touches the database configured in `.env`.
"""

import os
import sys

_profile = os.environ.get("DJANGO_ENV", "development").lower()

_is_test = "test" in sys.argv or "pytest" in sys.modules

if _profile in {"production", "prod"}:
    from .production import *  # noqa: F401,F403
elif _profile in {"test", "testing"} or _is_test:
    from .test import *  # noqa: F401,F403
else:
    from .development import *  # noqa: F401,F403
