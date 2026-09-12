from rest_framework.routers import DefaultRouter

from .views import HoldingViewSet, ValuationViewSet

router = DefaultRouter()
router.register(r"holdings", HoldingViewSet, basename="holding")
router.register(r"valuations", ValuationViewSet, basename="valuation")

urlpatterns = router.urls
