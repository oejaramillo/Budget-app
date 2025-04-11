from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# budget models   
class Currencies(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=8, unique=True)
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6)
    principal = models.BooleanField()  # Field indicating if this is the principal currency
    is_active = models.BooleanField(default=True)  # Added to manage currency activation status

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['principal'], 
                                    condition=models.Q(principal=True), 
                                    name='unique_principal_currency')
        ]  # Ensures only one principal currency can be active at a time

    def __str__(self):
        return self.name

class Accounts(models.Model):
    ACCOUNT_TYPES = [
        ('checking', 'Checking'),
        ('savings', 'Savings'),
        ('credit', 'Credit')
    ]  # Added account types for flexibility

    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Links each account to a user
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default='checking')  # Added account type
    created_date = models.DateTimeField(auto_now_add=True)
    balance = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.ForeignKey(Currencies, on_delete=models.PROTECT)  # Protects from accidental currency deletion
    institution = models.CharField(max_length=200, blank=True, null=True)  
    official_number = models.CharField(max_length=100, blank=True, null=True)  
    last_updated = models.DateTimeField(auto_now=True)  # Automatically updated when changes are made

    def __str__(self):
        return self.name
    
class Budgets(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Links each budget to a user
    name = models.CharField(max_length=100)
    max_amount = models.DecimalField(max_digits=20, decimal_places=2)
    min_amount = models.DecimalField(max_digits=20, decimal_places=2)

    # Adding validation
    def clean(self):
        if self.min_amount > self.max_amount:
            raise ValidationError('Min amount cannot be greater than max amount.')
        if self.end_date <= self.start_date:
            raise ValidationError('End date must be after start date.')

    currency = models.ForeignKey(Currencies, on_delete=models.PROTECT)  # Protects from currency deletion
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self):
        return self.name

class Categories(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Added user reference for multi-user systems
    name = models.CharField(max_length=100)
    budget = models.ForeignKey(Budgets, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.name
    
class Transactions(models.Model):
    account = models.ForeignKey(Accounts, on_delete=models.CASCADE)  # Transactions tied to specific accounts

    TRANSACTION_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('transfer', 'Transfer')
    ]
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)  # Type of transaction
    transaction_date = models.DateTimeField()
    created_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    description = models.TextField(blank=True, default="")  # Made non-nullable with a default blank string

    category = models.ForeignKey(Categories, on_delete=models.SET_NULL, blank=True, null=True)  # Can be null if category is deleted
    budget = models.ForeignKey(Budgets, on_delete=models.SET_NULL, blank=True, null=True)  # Same for budgets
    currency = models.ForeignKey(Currencies, on_delete=models.PROTECT)  # Protect currency relationships

    # Added user foreign key for extra isolation
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Ensure only user’s own transactions are visible

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"

    class Meta:
        indexes = [
            models.Index(fields=['transaction_date']),  # Indexed for faster query performance
        ]

class AccountBudget(models.Model):
    budget = models.ForeignKey(Budgets, on_delete=models.CASCADE)  # When a budget is deleted, remove this relation
    account = models.ForeignKey(Accounts, on_delete=models.CASCADE)  # Same for accounts

    # Enforcing that a single account can't be linked to the same budget more than once
    class Meta:
        unique_together = ('budget', 'account')  # Ensure no duplicate links between account and budget