from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CurrencyViewSet, AccountViewSet, BudgetViewSet, 
    CategoryViewSet, TransactionViewSet, AccountBudgetViewSet,
    LoginView, LogoutView, CustomTokenVerifyView
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
    path('api/login/', LoginView.as_view(), name='login'),
]
