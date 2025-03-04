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
from rest_framework.decorators import api_view, permission_classes


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
class CustomLoginView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                "access": str(refresh.access_token),  # Access Token
                "refresh": str(refresh),  # Refresh Token
                "message": "Login successful"
            }, status=status.HTTP_200_OK)

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

## API views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_accounts(request):
    try:
        # Get all accounts belonging to the authenticated user
        accounts = Accounts.objects.filter(user=request.user)

        if not accounts.exists():
            return Response({"message": "No accounts found"}, status=404)

        # Serialize the accounts data
        serializer = AccountsSerializer(accounts, many=True)

        return Response(serializer.data, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_total_balance(request):
    try:
        accounts = Accounts.objects.filter(user=request.user)

        if not accounts.exists():
            return Response({"message": "No accounts found"}, status=404)

        total_balance = sum(account.balance for account in accounts)
        
        return Response({
            "totalBalance": total_balance
        })
    
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_balance(request, account_name):
    try:
        # Ensure account name is properly formatted in case of special characters
        account_name = account_name.strip()

        # Fetch only one matching account for the authenticated user
        account = Accounts.objects.filter(user=request.user, name__iexact=account_name).first()

        if not account:
            return Response({"error": "Account not found"}, status=404)
        
        return Response({
            "accountName": account.name,
            "accountBalance": account.balance,
            "currency": account.currency.code
        })
    
    except Exception as e:
        print(f"Error fetching balance for {account_name}: {e}")  # ✅ Logs error for debugging
        return Response({"error": str(e)}, status=500)


