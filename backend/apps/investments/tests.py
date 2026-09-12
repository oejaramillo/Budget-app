"""Holdings, valuations and portfolio aggregation."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Account
from apps.currencies.models import Currency

from .models import Holding, Valuation


class InvestmentTestCase(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw-not-used-1234")
        self.bob = User.objects.create_user(username="bob", password="pw-not-used-1234")
        self.usd = Currency.objects.create(
            code="USD", name="US Dollar", exchange_rate=Decimal("1"), principal=True
        )
        self.eur = Currency.objects.create(code="EUR", name="Euro", exchange_rate=Decimal("0.5"))
        self.alice_broker = Account.objects.create(
            user=self.alice,
            name="Alice broker",
            account_type="investment",
            balance=Decimal("0.00"),
            currency=self.usd,
        )
        self.bob_broker = Account.objects.create(
            user=self.bob,
            name="Bob broker",
            account_type="investment",
            balance=Decimal("0.00"),
            currency=self.usd,
        )
        self.client.force_authenticate(self.alice)

    def payload(self, **overrides):
        data = {
            "symbol": "vwce",
            "name": "FTSE All-World",
            "kind": "etf",
            "quantity": "10.0000000000",
            "cost_basis": "1000.00",
            "currency": self.usd.pk,
            "account": self.alice_broker.pk,
            "opened_date": timezone.localdate().isoformat(),
        }
        data.update(overrides)
        return data


class HoldingTests(InvestmentTestCase):
    def test_symbol_is_normalised_to_uppercase(self):
        response = self.client.post("/api/v1/holdings/", self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["symbol"], "VWCE")

    def test_quantity_keeps_ten_decimal_places(self):
        response = self.client.post(
            "/api/v1/holdings/", self.payload(quantity="0.1234567891"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        holding = Holding.objects.get(pk=response.data["id"])
        self.assertEqual(holding.quantity, Decimal("0.1234567891"))

    def test_negative_quantity_is_rejected(self):
        response = self.client.post(
            "/api/v1/holdings/", self.payload(quantity="-1"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_use_another_users_account(self):
        response = self.client.post(
            "/api/v1/holdings/", self.payload(account=self.bob_broker.pk), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_is_scoped_to_the_user(self):
        Holding.objects.create(
            user=self.bob,
            symbol="AAPL",
            quantity=Decimal("1"),
            cost_basis=Decimal("100"),
            currency=self.usd,
        )
        response = self.client.get("/api/v1/holdings/")
        self.assertEqual(response.data["count"], 0)

    def test_market_value_falls_back_to_cost_basis(self):
        holding = Holding.objects.create(
            user=self.alice,
            symbol="VWCE",
            quantity=Decimal("10"),
            cost_basis=Decimal("1000.00"),
            currency=self.usd,
        )
        self.assertEqual(holding.market_value, Decimal("1000.00"))
        self.assertEqual(holding.unrealised_gain, Decimal("0.00"))

    def test_market_value_uses_the_latest_valuation(self):
        holding = Holding.objects.create(
            user=self.alice,
            symbol="VWCE",
            quantity=Decimal("10"),
            cost_basis=Decimal("1000.00"),
            currency=self.usd,
        )
        Valuation.objects.create(
            holding=holding, valued_on=timezone.localdate().replace(day=1), value=Decimal("1100.00")
        )
        Valuation.objects.create(
            holding=holding, valued_on=timezone.localdate(), value=Decimal("1250.00")
        )
        self.assertEqual(holding.market_value, Decimal("1250.00"))
        self.assertEqual(holding.unrealised_gain, Decimal("250.00"))
        self.assertEqual(holding.unrealised_gain_percent, Decimal("25.00"))

    def test_valuation_requires_numeric_value(self):
        holding = Holding.objects.create(
            user=self.alice,
            symbol="VWCE",
            quantity=Decimal("10"),
            cost_basis=Decimal("1000.00"),
            currency=self.usd,
        )
        response = self.client.post(
            "/api/v1/valuations/",
            {"holding": holding.pk, "valued_on": timezone.localdate().isoformat(), "value": "abc"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PortfolioTests(InvestmentTestCase):
    def setUp(self):
        super().setUp()
        self.etf = Holding.objects.create(
            user=self.alice,
            symbol="VWCE",
            name="FTSE All-World",
            kind="etf",
            quantity=Decimal("10"),
            cost_basis=Decimal("1000.00"),
            currency=self.usd,
        )
        Valuation.objects.create(
            holding=self.etf, valued_on=timezone.localdate(), value=Decimal("1250.00")
        )
        self.eur_holding = Holding.objects.create(
            user=self.alice,
            symbol="SAP",
            kind="stock",
            quantity=Decimal("5"),
            cost_basis=Decimal("500.00"),
            currency=self.eur,
        )
        Holding.objects.create(
            user=self.bob,
            symbol="TSLA",
            quantity=Decimal("1"),
            cost_basis=Decimal("9000.00"),
            currency=self.usd,
        )

    def test_portfolio_excludes_other_users(self):
        response = self.client.get("/api/v1/holdings/portfolio/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["holding_count"], 2)
        self.assertEqual(Decimal(str(response.data["total_cost_basis"])), Decimal("1500.00"))

    def test_portfolio_reports_gain_and_percentage(self):
        response = self.client.get("/api/v1/holdings/portfolio/")
        # 1250 (VWCE valuation) + 500 (SAP falls back to cost) = 1750
        self.assertEqual(Decimal(str(response.data["total_market_value"])), Decimal("1750.00"))
        self.assertEqual(Decimal(str(response.data["unrealised_gain"])), Decimal("250.00"))
        self.assertEqual(Decimal(str(response.data["unrealised_gain_percent"])), Decimal("16.67"))

    def test_portfolio_converts_into_a_target_currency(self):
        response = self.client.get("/api/v1/holdings/portfolio/?target=EUR")
        # SAP is already EUR (500). VWCE: 1250 USD at 0.5 EUR/USD = 625 EUR.
        self.assertEqual(Decimal(str(response.data["total_market_value"])), Decimal("1125.00"))
        self.assertEqual(response.data["target_currency"], "EUR")

    def test_portfolio_groups_by_kind(self):
        response = self.client.get("/api/v1/holdings/portfolio/")
        kinds = {row["kind"] for row in response.data["by_kind"]}
        self.assertEqual(kinds, {"etf", "stock"})

    def test_portfolio_rejects_unknown_target(self):
        response = self.client.get("/api/v1/holdings/portfolio/?target=XXX")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_history_lists_valuation_dates(self):
        response = self.client.get("/api/v1/holdings/history/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(Decimal(str(response.data[0]["value"])), Decimal("1250.00"))
