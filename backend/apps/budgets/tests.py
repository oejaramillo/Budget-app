"""Budget validation, ownership scoping and status reporting."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Account
from apps.currencies.models import Currency

from .models import Budget


class BudgetTestCase(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw-not-used-1234")
        self.bob = User.objects.create_user(username="bob", password="pw-not-used-1234")
        self.usd = Currency.objects.create(
            code="USD", name="US Dollar", exchange_rate=Decimal("1"), principal=True
        )
        self.alice_account = Account.objects.create(
            user=self.alice, name="Alice checking", balance=Decimal("1000.00"), currency=self.usd
        )
        self.bob_account = Account.objects.create(
            user=self.bob, name="Bob checking", balance=Decimal("100.00"), currency=self.usd
        )
        self.today = timezone.localdate()
        self.client.force_authenticate(self.alice)

    def payload(self, **overrides):
        data = {
            "name": "Monthly groceries",
            "min_amount": "0.00",
            "max_amount": "400.00",
            "currency": self.usd.pk,
            "start_date": self.today.replace(day=1).isoformat(),
            "end_date": self.today.isoformat(),
            "accounts": [self.alice_account.pk],
        }
        data.update(overrides)
        return data


class BudgetValidationTests(BudgetTestCase):
    def test_creates_a_budget_owned_by_the_request_user(self):
        response = self.client.post("/api/v1/budgets/", self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Budget.objects.get(pk=response.data["id"]).user, self.alice)

    def test_min_greater_than_max_is_rejected(self):
        response = self.client.post(
            "/api/v1/budgets/",
            self.payload(min_amount="500.00", max_amount="100.00"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("min_amount", response.data)

    def test_end_before_start_is_rejected(self):
        response = self.client.post(
            "/api/v1/budgets/",
            self.payload(start_date="2025-06-01", end_date="2025-01-01"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_date", response.data)

    def test_max_amount_must_be_positive(self):
        response = self.client.post(
            "/api/v1/budgets/",
            self.payload(min_amount="0.00", max_amount="0.00"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_link_another_users_account(self):
        response = self.client.post(
            "/api/v1/budgets/", self.payload(accounts=[self.bob_account.pk]), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BudgetIsolationTests(BudgetTestCase):
    def setUp(self):
        super().setUp()
        Budget.objects.create(
            user=self.bob,
            name="Bob budget",
            min_amount=Decimal("0"),
            max_amount=Decimal("50"),
            currency=self.usd,
            start_date=self.today,
            end_date=self.today,
        )

    def test_list_is_scoped_to_the_user(self):
        response = self.client.get("/api/v1/budgets/")
        self.assertEqual(response.data["count"], 0)

    def test_retrieve_of_another_users_budget_is_404(self):
        bob_budget = Budget.objects.get(user=self.bob)
        response = self.client.get(f"/api/v1/budgets/{bob_budget.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_of_another_users_budget_is_404(self):
        bob_budget = Budget.objects.get(user=self.bob)
        response = self.client.delete(f"/api/v1/budgets/{bob_budget.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Budget.objects.filter(pk=bob_budget.pk).exists())


class BudgetStatusTests(BudgetTestCase):
    def test_status_reports_spend_and_remaining(self):
        created = self.client.post("/api/v1/budgets/", self.payload(), format="json")
        budget_id = created.data["id"]

        self.client.post(
            "/api/v1/transactions/",
            {
                "account": self.alice_account.pk,
                "transaction_type": "expense",
                "transaction_date": self.today.isoformat(),
                "amount": "150.00",
                "budget": budget_id,
            },
            format="json",
        )

        response = self.client.get("/api/v1/budgets/status/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = next(item for item in response.data if item["id"] == budget_id)
        self.assertEqual(Decimal(str(row["spent_amount"])), Decimal("150.00"))
        self.assertEqual(Decimal(str(row["remaining_amount"])), Decimal("250.00"))
        self.assertEqual(row["percentage_used"], 37.5)
        self.assertFalse(row["is_over_budget"])

    def test_status_flags_overspending(self):
        created = self.client.post(
            "/api/v1/budgets/", self.payload(max_amount="100.00"), format="json"
        )
        budget_id = created.data["id"]
        self.client.post(
            "/api/v1/transactions/",
            {
                "account": self.alice_account.pk,
                "transaction_type": "expense",
                "transaction_date": self.today.isoformat(),
                "amount": "150.00",
                "budget": budget_id,
            },
            format="json",
        )
        response = self.client.get("/api/v1/budgets/status/")
        row = next(item for item in response.data if item["id"] == budget_id)
        self.assertTrue(row["is_over_budget"])
        self.assertEqual(Decimal(str(row["remaining_amount"])), Decimal("-50.00"))
