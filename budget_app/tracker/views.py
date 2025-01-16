from django.shortcuts import render
from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Currencies, Accounts, Budgets, Categories, Transactions, AccountBudget
from .serializers import (
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
    # authentication
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


## auth 
class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)

        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            return Response({"token": token.key, "message": "Login succesful"}, status=status.HTTP_200_OK)
        return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

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
        
class CustomTokenVerifyView(TokenVerifyView):
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except TokenError as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
