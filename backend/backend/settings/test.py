"""Settings used when running the test suite.

Why this exists: `DATABASE_URL` may point at a live Neon database. Django's test
runner would create a `test_<name>` database next to it and, on Neon's connection
pooler, often fail to drop it afterwards. Running the suite against production-adjacent
infrastructure is a foot-gun, so tests always use a throwaway local database unless
`DJANGO_TEST_USE_CONFIGURED_DB=1` is set explicitly.

`development` supplies the rest (DEBUG on, permissive CORS, console logging).
"""

import os
import sys

from .development import *  # noqa: F401,F403

# Reuse the live database only when a human asks for it on purpose.
if os.environ.get("DJANGO_TEST_USE_CONFIGURED_DB") != "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            # In-memory: the suite never creates a file, and nothing local can be
            # mistaken for real data.
            "NAME": ":memory:",
        }
    }

# Migrations are exercised by the suite itself; silence the per-migration chatter
# so failures are what stands out.
if "--verbosity" not in sys.argv:
    LOGGING = {  # noqa: F405
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {"console": {"class": "logging.StreamHandler"}},
        "root": {"handlers": ["console"], "level": "WARNING"},
    }

# Password hashing is intentionally slow. In tests it dominates the runtime, so use
# a fast (and deliberately insecure) hasher.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Throttling would make repeated login attempts inside one test flaky. The rate
# dictionary still has to contain every scope a view references, so disable the
# classes rather than emptying the rates.
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": (),
}
