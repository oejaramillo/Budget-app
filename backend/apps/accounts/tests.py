"""Account CRUD, ownership scoping and balance reporting."""

from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from apps.currencies.models import Currency

from .models import Account


class AccountIsolationTests(APITestCase):
    """The core multi-tenant guarantee: one user can never see another's data."""

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw-not-used-1234")
        self.bob = User.objects.create_user(username="bob", password="pw-not-used-1234")
        self.usd = Currency.objects.create(
            code="USD", name="US Dollar", exchange_rate=Decimal("1"), principal=True
        )
        self.alice_account = Account.objects.create(
            user=self.alice, name="Alice checking", balance=Decimal("100.00"), currency=self.usd
        )
        self.bob_account = Account.objects.create(
            user=self.bob, name="Bob checking", balance=Decimal("500.00"), currency=self.usd
        )

    def test_list_only_returns_own_accounts(self):
        self.client.force_authenticate(self.alice)
        response = self.client.get("/api/v1/accounts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Alice checking")

    def test_cannot_retrieve_another_users_account(self):
        self.client.force_authenticate(self.alice)
        response = self.client.get(f"/api/v1/accounts/{self.bob_account.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_update_another_users_account(self):
        self.client.force_authenticate(self.alice)
        response = self.client.patch(
            f"/api/v1/accounts/{self.bob_account.pk}/", {"name": "hijacked"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.bob_account.refresh_from_db()
        self.assertEqual(self.bob_account.name, "Bob checking")

    def test_cannot_delete_another_users_account(self):
        self.client.force_authenticate(self.alice)
        response = self.client.delete(f"/api/v1/accounts/{self.bob_account.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Account.objects.filter(pk=self.bob_account.pk).exists())

    def test_creating_an_account_assigns_the_request_user(self):
        self.client.force_authenticate(self.bob)
        response = self.client.post(
            "/api/v1/accounts/",
            {"name": "Bob savings", "account_type": "savings", "currency": self.usd.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Account.objects.get(pk=response.data["id"])
        self.assertEqual(created.user, self.bob)

    def test_user_field_cannot_be_spoofed(self):
        """Sending `user` in the body must not reassign the row to somebody else."""
        self.client.force_authenticate(self.alice)
        response = self.client.post(
            "/api/v1/accounts/",
            {
                "name": "Sneaky",
                "account_type": "checking",
                "currency": self.usd.pk,
                "user": self.bob.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Account.objects.get(pk=response.data["id"]).user, self.alice)


class AccountValidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="pw-not-used-1234")
        self.usd = Currency.objects.create(
            code="USD", name="US Dollar", exchange_rate=Decimal("1"), principal=True
        )
        self.client.force_authenticate(self.user)

    def test_balance_cannot_be_set_through_the_api(self):
        """Balances change through transactions, not arbitrary PUTs."""
        response = self.client.post(
            "/api/v1/accounts/",
            {
                "name": "Card",
                "account_type": "credit",
                "currency": self.usd.pk,
                "balance": "999999.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(str(response.data["balance"])), Decimal("0.00"))

    def test_adjust_balance_endpoint_sets_the_value(self):
        account = Account.objects.create(
            user=self.user, name="Cash", balance=Decimal("0.00"), currency=self.usd
        )
        response = self.client.post(
            f"/api/v1/accounts/{account.pk}/adjust-balance/",
            {"balance": "250.75"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal("250.75"))

    def test_adjust_balance_rejects_garbage(self):
        account = Account.objects.create(
            user=self.user, name="Cash", balance=Decimal("0.00"), currency=self.usd
        )
        response = self.client.post(
            f"/api/v1/accounts/{account.pk}/adjust-balance/",
            {"balance": "not-money"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_account_name_is_rejected(self):
        Account.objects.create(
            user=self.user, name="Wallet", balance=Decimal("0"), currency=self.usd
        )
        response = self.client.post(
            "/api/v1/accounts/",
            {"name": "Wallet", "account_type": "cash", "currency": self.usd.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_currency_is_rejected(self):
        response = self.client.post(
            "/api/v1/accounts/",
            {"name": "Ghost", "account_type": "cash", "currency": 99999},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_currency_is_rejected(self):
        old = Currency.objects.create(
            code="ATS", name="Schilling", exchange_rate=Decimal("13.76"), is_active=False
        )
        response = self.client.post(
            "/api/v1/accounts/",
            {"name": "Old", "account_type": "cash", "currency": old.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AccountReportingTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="pw-not-used-1234")
        self.usd = Currency.objects.create(
            code="USD", name="US Dollar", exchange_rate=Decimal("1"), principal=True
        )
        self.eur = Currency.objects.create(
            code="EUR", name="Euro", exchange_rate=Decimal("0.5")
        )
        Account.objects.create(
            user=self.user, name="USD wallet", balance=Decimal("100.00"), currency=self.usd
        )
        Account.objects.create(
            user=self.user, name="EUR wallet", balance=Decimal("100.00"), currency=self.eur
        )
        self.client.force_authenticate(self.user)

    def test_net_worth_lists_each_currency_separately(self):
        response = self.client.get("/api/v1/accounts/net-worth/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        totals = {row["currency"]: Decimal(str(row["total"])) for row in response.data["per_currency"]}
        self.assertEqual(totals, {"USD": Decimal("100.00"), "EUR": Decimal("100.00")})

    def test_net_worth_converts_when_a_target_is_given(self):
        # 100 EUR at 0.5 EUR/USD -> 200 USD, plus the 100 USD account = 300 USD
        response = self.client.get("/api/v1/accounts/net-worth/?target=USD")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(response.data["converted_total"])), Decimal("300.00"))

    def test_net_worth_rejects_unknown_target(self):
        response = self.client.get("/api/v1/accounts/net-worth/?target=XXX")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_balances_endpoint_reports_reference_values(self):
        response = self.client.get("/api/v1/accounts/balances/?target=USD")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        by_name = {row["account_name"]: row for row in response.data}
        self.assertEqual(
            Decimal(str(by_name["EUR wallet"]["reference_balance"])), Decimal("200.00")
        )
        self.assertEqual(
            Decimal(str(by_name["USD wallet"]["reference_balance"])), Decimal("100.00")
        )

    def test_pagination_wraps_list_responses(self):
        response = self.client.get("/api/v1/accounts/?page_size=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIsNotNone(response.data["next"])
