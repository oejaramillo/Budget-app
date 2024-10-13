from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CurrencyViewSet, AccountViewSet, BudgetViewSet, CategoryViewSet, TransactionViewSet, AccountBudgetViewSet

router = DefaultRouter()
router.register(r'currencies', CurrencyViewSet)
router.register(r'accounts', AccountViewSet)
router.register(r'budgets', BudgetViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'accounts-budgets', AccountBudgetViewSet)

urlpatterns = [
    path('api/v1/', include((router.urls, 'budget_app'))),
]
