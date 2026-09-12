from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, TransactionViewSet

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"transactions", TransactionViewSet, basename="transaction")

urlpatterns = router.urls
