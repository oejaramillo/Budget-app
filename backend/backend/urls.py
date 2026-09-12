"""Root URL configuration.

Everything the frontend consumes lives under `/api/v1/`. Versioning the API from
day one means a breaking change can ship as `/api/v2/` without breaking clients
that are already deployed.
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def api_root(_request):
    """Tiny unauthenticated index so hitting the base URL is not a 404."""
    return JsonResponse(
        {
            "name": "Budget App API",
            "version": "v1",
            "endpoints": {
                "auth": "/api/v1/auth/login/",
                "register": "/api/v1/auth/register/",
                "me": "/api/v1/auth/me/",
                "health": "/api/v1/health/",
                "currencies": "/api/v1/currencies/",
                "accounts": "/api/v1/accounts/",
                "budgets": "/api/v1/budgets/",
                "categories": "/api/v1/categories/",
                "transactions": "/api/v1/transactions/",
                "holdings": "/api/v1/holdings/",
                "valuations": "/api/v1/valuations/",
            },
            "docs": "https://github.com/oejaramillo/Budget-app#api-reference",
        }
    )


api_v1 = [
    path("", include("apps.users.urls")),
    path("", include("apps.currencies.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.budgets.urls")),
    path("", include("apps.transactions.urls")),
    path("", include("apps.investments.urls")),
]

urlpatterns = [
    path("", api_root, name="api-root"),
    path("admin/", admin.site.urls),
    path("api/v1/", include((api_v1, "v1"))),
]
