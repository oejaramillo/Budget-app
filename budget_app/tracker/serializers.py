from rest_framework import serializers
from .models import  Currencies, Accounts, Budgets, Categories, Transactions, AccountBudget

class CurrenciesSerializer(serializers.ModelSerializer):
    formatted_exchange_rate = serializers.SerializerMethodField()

    class Meta:
        model = Currencies
        fields = ['name', 'code', 'exchange_rate', 'formatted_exchange_rate', 'principal']
        read_only_fields = ['principal']

    def get_formatted_exchange_rate(self, obj):
        return f"{obj.exchange_rate:.6f}"
    
    def validate_principal(self, value):
        if value and Currencies.objects.filter(principal = True).exists():
            raise serializers.ValidationError("There can only be one principal currency.")
        return value

class AccountsSerializer(serializers.ModelSerializer):
    currency = serializers.PrimaryKeyRelatedField(read_only=True)
    account_type_display = serializers.SerializerMethodField()
    user = serializers.StringRelatedField()

    class Meta:
        model = Accounts
        fields = ['id', 'user', 'name', 'account_type', 'account_type_display', 'created_date', 'balance', 'currency', 'institution']
        read_only_fields = ['created_date', 'last_updated']
    
    def get_account_type_display(self, obj):
        return obj.get_account_type_display()

class BudgetsSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    currency = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Budgets
        fields = '__all__'

    def validate_amount(self, data):
        if data['min_amount'] > data['max_amount']:
            raise serializers.ValidationError("Mininmal amount cannot be bigger than the maximum value")
        
        if data['end_date'] <= data['start_date']:
            raise serializers.ValidationError("End date must be after start date")
        
        return data
    
    def validate_max_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError["Max amount must be positive."]
        return value 

class CategoriesSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    budget = serializers.PrimaryKeyRelatedField(read_only=True)
    # parent_category = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE) could be intersting in the future to define parent-child categories

    class Meta:
        model = Categories
        fields = '__all__'

class TransactionsSerializer(serializers.ModelSerializer):
    account = AccountsSerializer(read_only=True)
    category = CategoriesSerializer(read_only=True)
    budget = BudgetsSerializer(read_only=True)
    currency = CurrenciesSerializer(read_only=True)
    ttransaction_type_display = serializers.SerializerMethodField()

    class Meta:
        model = Transactions
        fields = ['id', 'account', 'transaction_type', 'transaction_type_display', 'transaction_date',
              'created_date', 'amount', 'description', 'category', 'budget', 'currency', 'user']
        read_only_fields = ['created_date', 'user', 'transaction_type_display']

    
    def get_transaction_type_display(self, obj):
        return obj.get_transaction_type_display()
    
    def validate(self, data):
        if data['account'].currency != data['currency']:
            raise serializers.ValidationError("Account currency must match transaction currency.")
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