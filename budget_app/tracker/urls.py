from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CurrencyViewSet, AccountViewSet, BudgetViewSet, CategoryViewSet, TransactionViewSet, AccountBudgetViewSet

router = DefaultRouter()
router.register(r'currencies', CurrencyViewSet, basename='currency')
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'budgets', BudgetViewSet, basename='budget')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'accounts-budgets', AccountBudgetViewSet, basename='account-budget')

urlpatterns = [
    path('api/v1/', include((router.urls, 'budget_app'))),
]
