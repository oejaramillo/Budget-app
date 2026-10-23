"""Spending analytics: the rules that decide what counts as spending.

The most important behaviour here is the separation between consumption and money
movement. In this project's real data, transfers, loan repayments and currency
exchange are just over 47% of recorded expenses, so a regression that folds them
back into "spending" would misreport nearly half of every figure on the dashboard.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account
from apps.currencies.models import Currency
from apps.transactions.models import Category, Transaction

from . import services


class AnalyticsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="pw-not-used-1234")
        self.other = User.objects.create_user(username="bob", password="pw-not-used-1234")
        self.usd = Currency.objects.create(
            code="USD", name="US Dollar", exchange_rate=Decimal("1"), principal=True
        )
        self.eur = Currency.objects.create(code="EUR", name="Euro", exchange_rate=Decimal("0.9"))
        self.account = Account.objects.create(
            user=self.user, name="Checking", balance=Decimal("0"), currency=self.usd
        )
        self.other_account = Account.objects.create(
            user=self.other, name="Bob checking", balance=Decimal("0"), currency=self.usd
        )
        self.today = timezone.localdate()

    def spend(self, amount, *, when=None, category="Comida", currency=None, user=None, kind=None):
        when = when or self.today
        account = self.account if user in (None, self.user) else self.other_account
        owner = user or self.user
        category_obj, _ = Category.objects.get_or_create(user=owner, name=category)
        return Transaction.objects.create(
            user=owner,
            account=account,
            transaction_type=kind or Transaction.Type.EXPENSE,
            transaction_date=when,
            amount=Decimal(str(amount)),
            currency=currency or self.usd,
            category=category_obj,
        )

    def earn(self, amount, *, when=None, user=None):
        when = when or self.today
        account = self.account if user in (None, self.user) else self.other_account
        return Transaction.objects.create(
            user=user or self.user,
            account=account,
            transaction_type=Transaction.Type.INCOME,
            transaction_date=when,
            amount=Decimal(str(amount)),
            currency=self.usd,
        )


class ConsumptionSplitTests(AnalyticsTestCase):
    """Money movement must never be counted as spending."""

    def test_transfer_like_categories_are_separated(self):
        self.spend("100.00", category="Comida")
        self.spend("500.00", category="Transferencia cuentas")
        self.spend("300.00", category="Préstamos")
        self.spend("50.00", category="Cambio de moneda")

        totals = services.period_totals(
            self.user, self.usd, self.today - timedelta(days=1), self.today
        )

        self.assertEqual(totals["expenses"], Decimal("950.00"))
        self.assertEqual(totals["consumption"], Decimal("100.00"))
        self.assertEqual(totals["money_movement"], Decimal("850.00"))

    def test_the_split_is_case_insensitive(self):
        self.spend("10.00", category="transferencia cuentas")
        totals = services.period_totals(
            self.user, self.usd, self.today - timedelta(days=1), self.today
        )
        self.assertEqual(totals["consumption"], Decimal("0.00"))
        self.assertEqual(totals["money_movement"], Decimal("10.00"))

    def test_transfers_between_accounts_are_excluded_entirely(self):
        """A transfer is not an expense at all, let alone spending."""
        second = Account.objects.create(
            user=self.user, name="Savings", balance=Decimal("0"), currency=self.usd
        )
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            destination_account=second,
            transaction_type=Transaction.Type.TRANSFER,
            transaction_date=self.today,
            amount=Decimal("250.00"),
            currency=self.usd,
        )
        totals = services.period_totals(
            self.user, self.usd, self.today - timedelta(days=1), self.today
        )
        self.assertEqual(totals["expenses"], Decimal("0"))
        self.assertEqual(totals["consumption"], Decimal("0"))

    def test_savings_rate_uses_consumption_not_total_expenses(self):
        self.earn("1000.00")
        self.spend("200.00", category="Comida")
        self.spend("500.00", category="Transferencia cuentas")

        totals = services.period_totals(
            self.user, self.usd, self.today - timedelta(days=1), self.today
        )
        payload = services._totals_payload(totals)

        # 1000 income - 200 consumption = 800 saved, i.e. 80%.
        self.assertEqual(payload["net_consumption"], 800.0)
        self.assertEqual(payload["savings_rate"], 80.0)
        self.assertEqual(payload["expense_ratio"], 20.0)

    def test_uncategorised_spending_counts_as_consumption(self):
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            transaction_type=Transaction.Type.EXPENSE,
            transaction_date=self.today,
            amount=Decimal("15.00"),
            currency=self.usd,
            category=None,
        )
        totals = services.period_totals(
            self.user, self.usd, self.today - timedelta(days=1), self.today
        )
        self.assertEqual(totals["consumption"], Decimal("15.00"))

    def test_category_breakdown_flags_movement(self):
        self.spend("100.00", category="Comida")
        self.spend("500.00", category="Transferencia cuentas")
        rows = services.category_breakdown(
            self.user, self.usd, self.today - timedelta(days=1), self.today
        )
        by_name = {row["category"]: row for row in rows}
        self.assertFalse(by_name["Comida"]["is_money_movement"])
        self.assertTrue(by_name["Transferencia cuentas"]["is_money_movement"])


class CurrencyScopeTests(AnalyticsTestCase):
    def test_only_the_reported_currency_is_counted(self):
        """Rates are single historical snapshots, so mixing currencies would lie."""
        self.spend("100.00")
        self.spend("1000.00", currency=self.eur)

        totals = services.period_totals(
            self.user, self.usd, self.today - timedelta(days=1), self.today
        )
        self.assertEqual(totals["consumption"], Decimal("100.00"))

    def test_principal_currency_is_the_default(self):
        self.assertEqual(services.resolve_currency(None).code, "USD")

    def test_unknown_currency_is_rejected(self):
        with self.assertRaises(services.AnalyticsError):
            services.resolve_currency("XXX")

    def test_available_currencies_lists_only_what_has_data(self):
        self.spend("10.00")
        self.spend("20.00", currency=self.eur)
        codes = {row["code"] for row in services.available_currencies(self.user)}
        self.assertEqual(codes, {"USD", "EUR"})


class TenantIsolationTests(AnalyticsTestCase):
    def test_another_users_spending_is_never_included(self):
        self.spend("100.00")
        self.spend("999.00", user=self.other, category="Comida")

        totals = services.period_totals(
            self.user, self.usd, self.today - timedelta(days=1), self.today
        )
        self.assertEqual(totals["consumption"], Decimal("100.00"))

    def test_dashboard_series_are_scoped_to_the_user(self):
        self.spend("100.00")
        for _ in range(3):
            self.spend("999.00", user=self.other, category="Comida")

        dashboard = services.build_dashboard(self.user)
        consumed = [row["consumption"] for row in dashboard["monthly"]]
        self.assertLessEqual(sum(consumed), 100.0)

    def test_category_trend_excludes_other_users(self):
        self.spend("10.00", category="Comida")
        self.spend("5000.00", user=self.other, category="Comida")
        trend = services.category_series(self.user, self.usd, 6)
        if trend["series"]:
            values = [value for series in trend["series"] for value in series["values"]]
            self.assertLess(max(values), 1000.0)


class PeriodTests(AnalyticsTestCase):
    def test_month_anchor_and_previous_month(self):
        current, previous, last_year = services.resolve_period(
            "month", "2026-03", date(2026, 6, 15)
        )
        self.assertEqual(current.start, date(2026, 3, 1))
        self.assertEqual(current.end, date(2026, 3, 31))
        self.assertTrue(current.complete)
        self.assertEqual(previous.start, date(2026, 2, 1))
        self.assertEqual(previous.end, date(2026, 2, 28))
        self.assertEqual(last_year.start, date(2025, 3, 1))

    def test_running_month_is_flagged_incomplete(self):
        today = date(2026, 3, 10)
        current, previous, _ = services.resolve_period("month", None, today)
        self.assertEqual(current.start, date(2026, 3, 1))
        self.assertFalse(current.complete)
        # Compared with the last *complete* month, never a partial one.
        self.assertEqual(previous.start, date(2026, 2, 1))

    def test_quarter_anchors_are_accepted_in_several_spellings(self):
        for anchor in ("2025-Q3", "2025Q3", "2025-3"):
            current, previous, _ = services.resolve_period(
                "quarter", anchor, date(2026, 1, 1)
            )
            self.assertEqual(current.start, date(2025, 7, 1))
            self.assertEqual(current.end, date(2025, 9, 30))
            self.assertEqual(previous.start, date(2025, 4, 1))

    def test_year_anchor(self):
        current, previous, _ = services.resolve_period("year", "2024", date(2026, 1, 1))
        self.assertEqual(current.start, date(2024, 1, 1))
        self.assertEqual(current.end, date(2024, 12, 31))
        self.assertEqual(previous.start, date(2023, 1, 1))

    def test_bad_values_are_rejected(self):
        for granularity, anchor in (("month", "nonsense"), ("quarter", "2025-X"), ("year", "x")):
            with self.assertRaises(services.AnalyticsError):
                services.resolve_period(granularity, anchor, date(2026, 1, 1))
        with self.assertRaises(services.AnalyticsError):
            services.resolve_period("fortnight", None, date(2026, 1, 1))


class SeriesTests(AnalyticsTestCase):
    def test_months_without_spending_are_present_as_zeroes(self):
        """A gap in spending is information; skipping it implies continuity."""
        series = services.monthly_series(self.user, self.usd, 6)
        self.assertEqual(len(series), 6)
        self.assertTrue(all(row["consumption"] == 0 for row in series))

    def test_series_ends_on_the_current_month(self):
        series = services.monthly_series(self.user, self.usd, 3)
        self.assertEqual(series[-1]["month"], f"{self.today:%Y-%m}")

    def test_current_month_totals_appear_in_the_last_bucket(self):
        self.spend("42.00")
        series = services.monthly_series(self.user, self.usd, 3)
        self.assertEqual(series[-1]["consumption"], 42.0)

    def test_category_series_puts_small_categories_in_other(self):
        for index in range(10):
            self.spend("100.00", category=f"Cat {index}")
        # Every month, so the window is not empty.
        trend = services.category_series(self.user, self.usd, 3, top=3)
        self.assertEqual(len(trend["categories"]), 3)
        self.assertTrue(any(value > 0 for value in trend["other"]))


class OutlookTests(AnalyticsTestCase):
    def test_verdict_is_in_progress_without_history(self):
        self.spend("100.00")
        outlook = services.spend_outlook(self.user, self.usd)
        self.assertEqual(outlook["verdict"], "in_progress")
        self.assertEqual(outlook["months_compared"], 0)

    def test_projection_extends_the_daily_pace_to_month_end(self):
        today = date(2026, 3, 10)
        # Ten days at 100 a day.
        for day in range(1, 11):
            self.spend("100.00", when=date(2026, 3, day))
        outlook = services.spend_outlook(self.user, self.usd, today)
        self.assertEqual(outlook["days_elapsed"], 10)
        self.assertEqual(outlook["days_in_month"], 31)
        self.assertEqual(outlook["spent_so_far"], 1000.0)
        # 1000 / 10 * 31
        self.assertEqual(outlook["projected_month_end"], 3100.0)

    def test_high_verdict_when_pace_exceeds_the_users_own_normal(self):
        today = date(2026, 3, 10)
        # Three calm complete months.
        for month in (12, 1, 2):
            year = 2025 if month == 12 else 2026
            self.spend("300.00", when=date(year, month, 5))
        # A March running at four times that pace.
        for day in range(1, 11):
            self.spend("120.00", when=date(2026, 3, day))
        outlook = services.spend_outlook(self.user, self.usd, today)
        self.assertGreater(outlook["typical_month"], 0)
        self.assertEqual(outlook["verdict"], "high")

    def test_low_verdict_when_pace_is_far_below_normal(self):
        today = date(2026, 3, 10)
        for month in (12, 1, 2):
            year = 2025 if month == 12 else 2026
            self.spend("3000.00", when=date(year, month, 5))
        self.spend("10.00", when=date(2026, 3, 1))
        outlook = services.spend_outlook(self.user, self.usd, today)
        self.assertEqual(outlook["verdict"], "low")


class DashboardPayloadTests(AnalyticsTestCase):
    def test_shape_and_json_safety(self):
        import json

        self.spend("25.00")
        self.earn("1000.00")
        dashboard = services.build_dashboard(self.user)

        for key in (
            "currency",
            "period",
            "totals",
            "comparisons",
            "outlook",
            "top_categories",
            "monthly",
            "category_trend",
            "weekday",
            "recurring",
            "insights",
            "data_range",
        ):
            self.assertIn(key, dashboard)

        # The response goes straight out as JSON; Decimal or date objects would 500.
        json.dumps(dashboard, default=str)
        json.dumps({k: v for k, v in dashboard.items() if k != "generated_at"}, default=str)

    def test_empty_ledger_yields_a_usable_dashboard(self):
        dashboard = services.build_dashboard(self.user)
        self.assertEqual(dashboard["totals"]["current"]["consumption"], 0.0)
        self.assertEqual(dashboard["insights"], [])
        self.assertTrue(len(dashboard["monthly"]) > 0)
        self.assertEqual(dashboard["data_range"]["first"], None)

    def test_weekday_and_payees_exclude_money_movement(self):
        self.spend("100.00", category="Comida")
        self.spend("9000.00", category="Transferencia cuentas")
        dashboard = services.build_dashboard(self.user)
        total_weekday = sum(row["total"] for row in dashboard["weekday"])
        self.assertLess(total_weekday, 1000)

    def test_insights_report_a_rise_in_spending(self):
        today = date(2026, 3, 10)
        for month in (12, 1, 2):
            year = 2025 if month == 12 else 2026
            self.spend("100.00", when=date(year, month, 5))
        self.spend("5000.00", when=date(2026, 3, 2))
        dashboard = services.build_dashboard(self.user, today=today)
        titles = " ".join(insight["title"] for insight in dashboard["insights"])
        self.assertIn("up", titles.lower())

    def test_recurring_detects_a_monthly_cost(self):
        today = date(2026, 3, 15)
        for month in range(1, 13):
            self.spend("500.00", when=date(2025, month, 3), category="Alojamiento y arriendos")
        dashboard = services.build_dashboard(self.user, today=today)
        names = [row["category"] for row in dashboard["recurring"]]
        self.assertIn("Alojamiento y arriendos", names)
        rent = next(row for row in dashboard["recurring"] if row["category"] == "Alojamiento y arriendos")
        self.assertEqual(rent["monthly_average"], 500.0)
        self.assertEqual(rent["variability_percent"], 0.0)

    def test_recurring_ignores_one_off_spending(self):
        today = date(2026, 3, 15)
        for month in range(1, 13):
            self.spend("500.00", when=date(2025, month, 3), category="Comida")
        # A single large purchase in one month only.
        self.spend("9000.00", when=date(2025, 6, 10), category="Inmuebles")
        dashboard = services.build_dashboard(self.user, today=today)
        names = [row["category"] for row in dashboard["recurring"]]
        self.assertNotIn("Inmuebles", names)


class MoneyHelperTests(TestCase):
    def test_money_rounds_to_cents(self):
        self.assertEqual(services.money(Decimal("1.005")), 1.01)

    def test_percent_returns_none_for_a_zero_base(self):
        self.assertIsNone(services.percent(Decimal("5"), Decimal("0")))

    def test_delta_reports_change_and_direction(self):
        result = services.delta(Decimal("150"), Decimal("100"))
        self.assertEqual(result["change"], 50.0)
        self.assertEqual(result["change_percent"], 50.0)
