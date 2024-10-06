from django.db import models
from django.contrib.auth.models import User

class Currencies(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=8, unique=True)
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6)
    principal = models.BooleanField()
    is_active = models.BooleanField(default=True)  # Added to manage currency activation status

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['principal'], condition=models.Q(principal=True), name='unique_principal_currency')
        ]  # Ensures only one principal currency can be active

    def __str__(self):
        return self.name

class Accounts(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created_date = models.DateTimeField(auto_now_add=True)
    balance = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.ForeignKey(Currencies, on_delete=models.PROTECT)  
    institution = models.CharField(max_length=200, blank=True, null=True)  
    official_number = models.CharField(max_length=100, blank=True, null=True)  
    last_updated = models.DateTimeField(auto_now=True)  # Added to track balance update time

    def __str__(self):
        return self.name
    
class Budgets(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Added user field to tie budgets to users
    name = models.CharField(max_length=100)
    max_amount = models.DecimalField(max_digits=20, decimal_places=2)
    min_amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.ForeignKey(Currencies, on_delete=models.PROTECT) 
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self):
        return self.name
    
class Categories(models.Model):
    name = models.CharField(max_length=100)
    budget = models.ForeignKey(Budgets, on_delete=models.CASCADE) 

    def __str__(self):
        return self.name
    
class Transactions(models.Model):
    account = models.ForeignKey(Accounts, on_delete=models.CASCADE)
    TRANSACTION_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('transfer', 'Transfer')
    ]
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    transaction_date = models.DateTimeField()
    created_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    description = models.TextField(blank=True, default="")  
    category = models.ForeignKey(Categories, on_delete=models.SET_NULL, blank=True, null=True)  
    budget = models.ForeignKey(Budgets, on_delete=models.SET_NULL, blank=True, null=True) 
    currency = models.ForeignKey(Currencies, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"

    class Meta:
        indexes = [
            models.Index(fields=['transaction_date']),  # Added index for faster query
        ]
    
class AccountBudget(models.Model):
    budget = models.ForeignKey(Budgets, on_delete=models.CASCADE) 
    account = models.ForeignKey(Accounts, on_delete=models.CASCADE)  

