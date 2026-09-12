from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import OperationViewSet, OpsSettingsView, SystemOverviewView, TenantViewSet

router = DefaultRouter()
router.register(r"ops/operations", OperationViewSet, basename="ops-operation")
router.register(r"ops/tenants", TenantViewSet, basename="ops-tenant")

urlpatterns = [
    path("ops/overview/", SystemOverviewView.as_view(), name="ops-overview"),
    path("ops/settings/", OpsSettingsView.as_view(), name="ops-settings"),
    *router.urls,
]
