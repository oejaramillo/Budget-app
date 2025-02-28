from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CurrencyViewSet, AccountViewSet, BudgetViewSet, 
    CategoryViewSet, TransactionViewSet, AccountBudgetViewSet,
    CustomLoginView, LogoutView, CustomTokenVerifyView, 
    get_total_balance, get_balance, get_user_accounts
)
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView

router = DefaultRouter()
router.register(r'currencies', CurrencyViewSet, basename='currency')
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'budgets', BudgetViewSet, basename='budget')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'accounts-budgets', AccountBudgetViewSet, basename='account-budget')

urlpatterns = [
    path('api/v1/', include((router.urls, 'budget_app'))),
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/token/verify/', CustomTokenVerifyView.as_view(), name='token_verify'),
    path('api/v1/auth/logout', LogoutView.as_view(), name='logout'),
    path('api/v1/auth/token/', CustomLoginView.as_view(), name='token_obtain_pair'),
    
    path('api/v1/accounts/', get_user_accounts, name='get-user-accounts'),

    path('api/v1/dashboard/total_balance/', get_total_balance, name='dashboard-balances'),
    path('api/v1/accounts/balance/<str:account_name>/', get_balance, name='get-account-balance'),

]
