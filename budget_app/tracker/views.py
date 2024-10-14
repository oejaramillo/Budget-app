from django.shortcuts import render
from rest_framework import viewsets, filters, status
from .models import Currencies, Accounts, Budgets, Categories, Transactions, AccountBudget
from .serializers import (
    CurrenciesSerializer, AccountsSerializer, BudgetsSerializer, 
    CategoriesSerializer, TransactionsSerializer, 
    AccountBudgetSerializer, CustomTokenObtainPairSerializer,
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response

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

class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['name', 'start_date', 'end_date', 'max_amount', 'min_amount']
    search_fields = ['name']
    ordering_fields = ['start_date', 'end_date', 'max_amount']

    def get_queryset(self):
        return Budgets.objects.filter(user=self.request.user).select_related('currency')

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategoriesSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        return Categories.objects.filter(user=self.request.user)

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionsSerializer
    # authentication
    permission_classes = [IsAuthenticated]
    # To avoid returning too much data  
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account', 'category', 'budget', 'transaction_type', 'transaction_date']
    search_fields = ['description', 'category']
    ordering_fields = ['transaction_date', 'amount']

    def get_queryset(self):
        return Transactions.objects.filter(user=self.request.user).select_related('account', 'category', 'budget', 'currency')

class AccountBudgetViewSet(viewsets.ModelViewSet):
    queryset = AccountBudget.objects.all()
    serializer_class = AccountBudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AccountBudget.objects.filter(account__user=self.request.user, budget__user=self.request.user).select_related('account', 'budget')


## auth custom view

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # get the refresh token
            refresh_token = request.data["refresh"]
            # blacklist the token
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)