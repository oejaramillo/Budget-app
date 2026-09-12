"""Transaction rules: cross-user isolation, balance effects and reporting."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Account
from apps.budgets.models import Budget
from apps.currencies.models import Currency

from .models import Category, Transaction


class TransactionBaseTestCase(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw-not-used-1234")
        self.bob = User.objects.create_user(username="bob", password="pw-not-used-1234")
        self.usd = Currency.objects.create(
            code="USD", name="US Dollar", exchange_rate=Decimal("1"), principal=True
        )
        self.eur = Currency.objects.create(code="EUR", name="Euro", exchange_rate=Decimal("2"))

        self.alice_account = Account.objects.create(
            user=self.alice, name="Alice checking", balance=Decimal("1000.00"), currency=self.usd
        )
        self.alice_savings = Account.objects.create(
            user=self.alice, name="Alice savings", balance=Decimal("500.00"), currency=self.usd
        )
        self.bob_account = Account.objects.create(
            user=self.bob, name="Bob checking", balance=Decimal("100.00"), currency=self.usd
        )
        self.alice_category = Category.objects.create(user=self.alice, name="Groceries")
        self.bob_category = Category.objects.create(user=self.bob, name="Bob only")

    def url(self):
        return "/api/v1/transactions/"

    def payload(self, **overrides):
        data = {
            "account": self.alice_account.pk,
            "transaction_type": "expense",
            "transaction_date": timezone.localdate().isoformat(),
            "amount": "25.50",
            "description": "Weekly shop",
            "category": self.alice_category.pk,
        }
        data.update(overrides)
        return data


class TransactionIsolationTests(TransactionBaseTestCase):
    """A crafted request must never reach another tenant's money."""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.alice)

    def test_cannot_spend_from_another_users_account(self):
        response = self.client.post(
            self.url(), self.payload(account=self.bob_account.pk), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.bob_account.refresh_from_db()
        self.assertEqual(self.bob_account.balance, Decimal("100.00"))

    def test_cannot_use_another_users_category(self):
        response = self.client.post(
            self.url(), self.payload(category=self.bob_category.pk), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_transfer_into_another_users_account(self):
        response = self.client.post(
            self.url(),
            self.payload(transaction_type="transfer", destination_account=self.bob_account.pk),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.bob_account.refresh_from_db()
        self.assertEqual(self.bob_account.balance, Decimal("100.00"))

    def test_cannot_attach_another_users_budget(self):
        bob_budget = Budget.objects.create(
            user=self.bob,
            name="Bob budget",
            min_amount=Decimal("0"),
            max_amount=Decimal("100"),
            currency=self.usd,
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
        )
        response = self.client.post(
            self.url(), self.payload(budget=bob_budget.pk), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_only_returns_own_transactions(self):
        Transaction.objects.create(
            user=self.bob,
            account=self.bob_account,
            transaction_type="income",
            transaction_date=timezone.localdate(),
            amount=Decimal("10.00"),
            currency=self.usd,
        )
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_cannot_read_another_users_transaction(self):
        bob_tx = Transaction.objects.create(
            user=self.bob,
            account=self.bob_account,
            transaction_type="income",
            transaction_date=timezone.localdate(),
            amount=Decimal("10.00"),
            currency=self.usd,
        )
        response = self.client.get(f"{self.url()}{bob_tx.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_field_cannot_be_spoofed(self):
        response = self.client.post(
            self.url(), self.payload(user=self.bob.pk), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Transaction.objects.get(pk=response.data["id"]).user, self.alice)


class TransactionBalanceTests(TransactionBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.alice)

    def test_expense_reduces_the_account_balance(self):
        response = self.client.post(
            self.url(), self.payload(amount="25.50"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.alice_account.refresh_from_db()
        self.assertEqual(self.alice_account.balance, Decimal("974.50"))

    def test_income_increases_the_account_balance(self):
        response = self.client.post(
            self.url(),
            self.payload(transaction_type="income", amount="200.00", category=None),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.alice_account.refresh_from_db()
        self.assertEqual(self.alice_account.balance, Decimal("1200.00"))

    def test_transfer_moves_money_between_own_accounts(self):
        response = self.client.post(
            self.url(),
            self.payload(
                transaction_type="transfer",
                amount="100.00",
                category=None,
                destination_account=self.alice_savings.pk,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.alice_account.refresh_from_db()
        self.alice_savings.refresh_from_db()
        self.assertEqual(self.alice_account.balance, Decimal("900.00"))
        self.assertEqual(self.alice_savings.balance, Decimal("600.00"))

    def test_deleting_a_transaction_reverts_the_balance(self):
        created = self.client.post(self.url(), self.payload(amount="25.50"), format="json")
        response = self.client.delete(f"{self.url()}{created.data['id']}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.alice_account.refresh_from_db()
        self.assertEqual(self.alice_account.balance, Decimal("1000.00"))

    def test_updating_the_amount_adjusts_the_balance(self):
        created = self.client.post(self.url(), self.payload(amount="25.50"), format="json")
        response = self.client.patch(
            f"{self.url()}{created.data['id']}/", {"amount": "50.00"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.alice_account.refresh_from_db()
        self.assertEqual(self.alice_account.balance, Decimal("950.00"))

    def test_balance_is_decimal_not_float(self):
        self.client.post(
            self.url(), self.payload(amount="0.10"), format="json"
        )
        self.client.post(
            self.url(), self.payload(amount="0.20"), format="json"
        )
        self.alice_account.refresh_from_db()
        # 1000 - 0.10 - 0.20 must be exactly 999.70, which floats would break.
        self.assertEqual(self.alice_account.balance, Decimal("999.70"))


class TransactionRuleTests(TransactionBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.alice)

    def test_amount_must_be_positive(self):
        response = self.client.post(self.url(), self.payload(amount="-5"), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zero_amount_is_rejected(self):
        response = self.client.post(self.url(), self.payload(amount="0"), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_requires_a_destination(self):
        response = self.client.post(
            self.url(), self.payload(transaction_type="transfer", category=None), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_to_the_same_account_is_rejected(self):
        response = self.client.post(
            self.url(),
            self.payload(
                transaction_type="transfer",
                category=None,
                destination_account=self.alice_account.pk,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_cannot_be_categorised(self):
        response = self.client.post(
            self.url(),
            self.payload(
                transaction_type="transfer", destination_account=self.alice_savings.pk
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_foreign_currency_requires_an_explicit_rate(self):
        response = self.client.post(
            self.url(), self.payload(currency=self.eur.pk), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exchange_rate", response.data)

    def test_foreign_currency_with_a_rate_is_accepted(self):
        response = self.client.post(
            self.url(),
            self.payload(currency=self.eur.pk, exchange_rate="2.0"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_account_currency_is_the_default(self):
        response = self.client.post(self.url(), self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["currency"], self.usd.pk)

    def test_signed_amount_is_negative_for_expenses(self):
        response = self.client.post(self.url(), self.payload(amount="10.00"), format="json")
        self.assertEqual(Decimal(str(response.data["signed_amount"])), Decimal("-10.00"))

    def test_bulk_create_is_atomic_on_failure(self):
        before = self.alice_account.balance
        response = self.client.post(
            self.url() + "bulk/",
            [
                self.payload(amount="10.00"),
                self.payload(amount="-999"),  # invalid, must abort the batch
            ],
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.alice_account.refresh_from_db()
        self.assertEqual(self.alice_account.balance, before)


class TransactionReportingTests(TransactionBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.alice)
        today = timezone.localdate()
        Transaction.objects.create(
            user=self.alice,
            account=self.alice_account,
            transaction_type="income",
            transaction_date=today,
            amount=Decimal("3000.00"),
            currency=self.usd,
        )
        Transaction.objects.create(
            user=self.alice,
            account=self.alice_account,
            transaction_type="expense",
            transaction_date=today,
            amount=Decimal("200.00"),
            currency=self.usd,
            category=self.alice_category,
        )
        Transaction.objects.create(
            user=self.bob,
            account=self.bob_account,
            transaction_type="income",
            transaction_date=today,
            amount=Decimal("9999.00"),
            currency=self.usd,
        )

    def test_summary_excludes_other_users(self):
        response = self.client.get("/api/v1/transactions/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(response.data["total_income"])), Decimal("3000.00"))
        self.assertEqual(Decimal(str(response.data["total_expenses"])), Decimal("200.00"))
        self.assertEqual(Decimal(str(response.data["net"])), Decimal("2800.00"))
        self.assertEqual(response.data["transaction_count"], 2)

    def test_summary_breaks_down_by_category(self):
        response = self.client.get("/api/v1/transactions/summary/")
        categories = {row["category_name"]: row for row in response.data["by_category"]}
        self.assertIn("Groceries", categories)
        self.assertEqual(Decimal(str(categories["Groceries"]["total"])), Decimal("200.00"))

    def test_summary_rejects_an_inverted_range(self):
        today = timezone.localdate().isoformat()
        response = self.client.get(f"/api/v1/transactions/summary/?start={today}&end=2000-01-01")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_monthly_returns_buckets(self):
        response = self.client.get("/api/v1/transactions/monthly/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(Decimal(str(response.data[0]["income"])), Decimal("3000.00"))
        self.assertEqual(Decimal(str(response.data[0]["expenses"])), Decimal("200.00"))

    def test_monthly_rejects_non_numeric_months(self):
        response = self.client.get("/api/v1/transactions/monthly/?months=many")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filters_by_account(self):
        response = self.client.get(f"/api/v1/transactions/?account={self.alice_account.pk}")
        self.assertEqual(response.data["count"], 2)


class CategoryTests(TransactionBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.alice)

    def test_duplicate_name_is_rejected(self):
        response = self.client.post(
            "/api/v1/categories/", {"name": "Groceries"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_attach_to_another_users_budget(self):
        bob_budget = Budget.objects.create(
            user=self.bob,
            name="Bob budget",
            min_amount=Decimal("0"),
            max_amount=Decimal("100"),
            currency=self.usd,
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
        )
        response = self.client.post(
            "/api/v1/categories/",
            {"name": "Dining", "budget": bob_budget.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_categories_are_listed_per_user(self):
        response = self.client.get("/api/v1/categories/")
        names = {row["name"] for row in response.data["results"]}
        self.assertEqual(names, {"Groceries"})
