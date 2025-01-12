import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_app.settings')
django.setup()

from tracker.models import Currencies, Accounts, Budgets, Categories, Transactions, AccountBudget
from django.contrib.auth.models import User

def create_database():
    if not User.objects.filter(username='admin').exists():
        User.objects.create_user(username='admin', password='admin', is_superuser=True, is_staff=True)
        print("User created")

if __name__ == '__main__':
    create_database()