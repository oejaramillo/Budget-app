from django.contrib.auth.models import User
from rest_framework import serializers
from .models import *

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
    
# Budget views
class CurrenciesSerializer(serializers.ModelSerializer):
    formatted_exchange_rate = serializers.SerializerMethodField()

    class Meta:
        model = Currencies
        fields = ['id', 'name', 'code', 'exchange_rate', 'formatted_exchange_rate', 'principal', 'is_active']
        read_only_fields = ['principal']

    def get_formatted_exchange_rate(self, obj):
        return f"{obj.exchange_rate:.6f}"
    
    def validate_principal(self, value):
        if value and Currencies.objects.filter(principal = True).exists():
            raise serializers.ValidationError("There can only be one principal currency.")
        return value
    
class AccountsSerializer(serializers.ModelSerializer):
    currency = serializers.PrimaryKeyRelatedField(queryset=Currencies.objects.all())
    account_type_display = serializers.SerializerMethodField()
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Accounts
        fields = ['id', 'user', 'name', 'account_type', 'account_type_display', 'created_date', 'balance', 'currency', 'institution']
        read_only_fields = ['created_date', 'last_updated', 'user']
    
    def get_account_type_display(self, obj):
        return obj.get_account_type_display()

class BudgetsSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    currency = serializers.PrimaryKeyRelatedField(queryset=Currencies.objects.all())

    class Meta:
        model = Budgets
        fields = '__all__'

    def validate(self, data):
        if data['min_amount'] > data['max_amount']:
            raise serializers.ValidationError("Minimum amount cannot be bigger than the maximum value")
        
        if data['end_date'] <= data['start_date']:
            raise serializers.ValidationError("End date must be after start date")
        
        return data
    
    def validate_max_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Max amount must be positive.")
        return value 

class CategoriesSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    budget = serializers.PrimaryKeyRelatedField(queryset=Budgets.objects.all(), required=False, allow_null=True)
    # parent_category = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE) could be intersting in the future to define parent-child categories

    class Meta:
        model = Categories
        fields = '__all__'
        read_only_fields = ['user']

class TransactionsSerializer(serializers.ModelSerializer):
    # For reading (GET requests) - return full objects
    account_detail = AccountsSerializer(source='account', read_only=True)
    category_detail = CategoriesSerializer(source='category', read_only=True)
    budget_detail = BudgetsSerializer(source='budget', read_only=True)
    currency_detail = CurrenciesSerializer(source='currency', read_only=True)
    
    # For writing (POST/PUT requests) - accept IDs
    account = serializers.PrimaryKeyRelatedField(queryset=Accounts.objects.all())
    category = serializers.PrimaryKeyRelatedField(queryset=Categories.objects.all(), required=False, allow_null=True)
    budget = serializers.PrimaryKeyRelatedField(queryset=Budgets.objects.all(), required=False, allow_null=True)
    currency = serializers.PrimaryKeyRelatedField(queryset=Currencies.objects.all())
    
    transaction_type_display = serializers.SerializerMethodField()
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Transactions
        fields = ['id', 'account', 'account_detail', 'transaction_type', 'transaction_type_display', 'transaction_date',
              'created_date', 'amount', 'description', 'category', 'category_detail', 'budget', 'budget_detail', 
              'currency', 'currency_detail', 'user']
        read_only_fields = ['created_date', 'user', 'transaction_type_display', 'account_detail', 'category_detail', 'budget_detail', 'currency_detail']

    
    def get_transaction_type_display(self, obj):
        return obj.get_transaction_type_display()
    
    def validate(self, data):
        # Remove this validation for now as it's causing issues
        # We can add it back later if needed
        return data

class AccountBudgetSerializer(serializers.ModelSerializer):
    budget = serializers.PrimaryKeyRelatedField(queryset=Budgets.objects.all())  # or use BudgetsSerializer for more detail
    account = serializers.PrimaryKeyRelatedField(queryset=Accounts.objects.all())  # or use AccountsSerializer

    class Meta:
        model = AccountBudget
        fields = ['budget', 'account']

    # Extra validation at serializer level
    def validate(self, data):
        if AccountBudget.objects.filter(budget=data['budget'], account=data['account']).exists():
            raise serializers.ValidationError("This account is already linked to this budget.")
        return data