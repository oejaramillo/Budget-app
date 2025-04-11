from django.shortcuts import render
from rest_framework import viewsets, filters, status, generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import (
    Currencies, Accounts, Budgets, Categories, Transactions, AccountBudget
)
from .serializers import (
    UserSerializer,
    CurrenciesSerializer, AccountsSerializer, BudgetsSerializer, 
    CategoriesSerializer, TransactionsSerializer, 
    AccountBudgetSerializer
)
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from rest_framework_simplejwt.views import TokenObtainPairView, TokenVerifyView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes

class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

## DATABASE views
class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Currencies.objects.all()
    serializer_class = CurrenciesSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['code', 'is_active', 'principal']
    search_fields = ['name', 'code']

class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['account_type', 'balance', 'currency', 'institution', 'official_number']
    search_fields = ['name', 'institution', 'last_updated']
    ordering_fields = ['balance', 'created_date', 'last_updated']

    def get_queryset(self):
        return Accounts.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['name', 'start_date', 'end_date', 'max_amount', 'min_amount']
    search_fields = ['name']
    ordering_fields = ['start_date', 'end_date', 'max_amount']

    def get_queryset(self):
        return Budgets.objects.filter(user=self.request.user).select_related('currency')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategoriesSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        return Categories.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionsSerializer
    permission_classes = [IsAuthenticated]
    # To avoid returning too much data  
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account', 'category', 'budget', 'transaction_type', 'transaction_date']
    search_fields = ['description', 'category']
    ordering_fields = ['transaction_date', 'amount']

    def get_queryset(self):
        return Transactions.objects.filter(user=self.request.user).select_related('account', 'category', 'budget', 'currency')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class AccountBudgetViewSet(viewsets.ModelViewSet):
    queryset = AccountBudget.objects.all()
    serializer_class = AccountBudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AccountBudget.objects.filter(account__user=self.request.user, budget__user=self.request.user).select_related('account', 'budget')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    