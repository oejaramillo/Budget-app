from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AnalyticsViewSet, SpendingView

router = DefaultRouter()
router.register(r"analytics", AnalyticsViewSet, basename="analytics")

urlpatterns = [
    path("analytics/spending/", SpendingView.as_view(), name="analytics-spending"),
    *router.urls,
]
