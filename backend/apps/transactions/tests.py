"""Transaction rules: cross-user isolation, balance effects and reporting."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models.functions import TruncMonth
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


class TransactionFilterTests(TransactionBaseTestCase):
    """Querystring filtering: the list endpoint is the app's busiest screen."""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.alice)
        for day, amount in (
            ("2026-01-05", "10.00"),
            ("2026-01-20", "20.00"),
            ("2026-02-03", "30.00"),
            ("2026-03-11", "40.00"),
        ):
            Transaction.objects.create(
                user=self.alice,
                account=self.alice_account,
                transaction_type=Transaction.Type.EXPENSE,
                transaction_date=day,
                amount=Decimal(amount),
                currency=self.usd,
                description=f"entry {day}",
                category=self.alice_category,
            )

    def test_date_range(self):
        response = self.client.get(
            "/api/v1/transactions/?date_from=2026-01-10&date_to=2026-02-28"
        )
        self.assertEqual(response.data["count"], 2)

    def test_single_month_shorthand(self):
        response = self.client.get("/api/v1/transactions/?month=2026-01")
        self.assertEqual(response.data["count"], 2)

    def test_invalid_month_returns_nothing(self):
        response = self.client.get("/api/v1/transactions/?month=nonsense")
        self.assertEqual(response.data["count"], 0)

    def test_amount_range(self):
        response = self.client.get("/api/v1/transactions/?amount_min=20&amount_max=30")
        self.assertEqual(response.data["count"], 2)

    def test_ordering_by_amount(self):
        response = self.client.get("/api/v1/transactions/?ordering=-amount")
        amounts = [Decimal(row["amount"]) for row in response.data["results"]]
        self.assertEqual(amounts, sorted(amounts, reverse=True))

    def test_search_matches_description(self):
        response = self.client.get("/api/v1/transactions/?search=2026-01-20")
        self.assertEqual(response.data["count"], 1)

    def test_filters_can_be_combined(self):
        response = self.client.get(
            "/api/v1/transactions/?month=2026-02&transaction_type=expense&amount_min=25"
        )
        self.assertEqual(response.data["count"], 1)

    def test_uncategorised_filter(self):
        Transaction.objects.create(
            user=self.alice,
            account=self.alice_account,
            transaction_type=Transaction.Type.EXPENSE,
            transaction_date="2026-04-01",
            amount=Decimal("5.00"),
            currency=self.usd,
            description="no category",
            category=None,
        )
        response = self.client.get("/api/v1/transactions/?uncategorised=true")
        self.assertEqual(response.data["count"], 1)


class DescriptionSuggestionTests(TransactionBaseTestCase):
    """Autocomplete data for the logging form."""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.alice)
        for description, account in (
            ("Starbucks", self.alice_account),
            ("Starbucks", self.alice_account),
            ("Starbucks", self.alice_savings),
            ("Uber", self.alice_account),
            ("", self.alice_account),  # blank descriptions are not suggestions
        ):
            Transaction.objects.create(
                user=self.alice,
                account=account,
                transaction_type=Transaction.Type.EXPENSE,
                transaction_date="2026-01-05",
                amount=Decimal("5.00"),
                currency=self.usd,
                description=description,
            )

    def test_returns_descriptions_most_used_first(self):
        response = self.client.get("/api/v1/transactions/descriptions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["description"] for row in response.data], ["Starbucks", "Uber"])
        self.assertEqual(response.data[0]["uses"], 3)

    def test_prefix_filter(self):
        response = self.client.get("/api/v1/transactions/descriptions/?q=star")
        self.assertEqual([row["description"] for row in response.data], ["Starbucks"])

    def test_filter_by_account(self):
        response = self.client.get(
            f"/api/v1/transactions/descriptions/?account={self.alice_savings.pk}"
        )
        self.assertEqual([row["description"] for row in response.data], ["Starbucks"])
        self.assertEqual(response.data[0]["uses"], 1)

    def test_limit_is_clamped(self):
        response = self.client.get("/api/v1/transactions/descriptions/?limit=1")
        self.assertEqual(len(response.data), 1)

    def test_rejects_non_numeric_limit(self):
        response = self.client.get("/api/v1/transactions/descriptions/?limit=many")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_never_leaks_another_users_descriptions(self):
        Transaction.objects.create(
            user=self.bob,
            account=self.bob_account,
            transaction_type=Transaction.Type.EXPENSE,
            transaction_date="2026-01-05",
            amount=Decimal("5.00"),
            currency=self.usd,
            description="Bob secret",
        )
        response = self.client.get("/api/v1/transactions/descriptions/")
        self.assertNotIn("Bob secret", [row["description"] for row in response.data])

    def test_recent_returns_newest_first(self):
        response = self.client.get("/api/v1/transactions/recent/?limit=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_recent_never_leaks_another_users_rows(self):
        Transaction.objects.create(
            user=self.bob,
            account=self.bob_account,
            transaction_type=Transaction.Type.EXPENSE,
            transaction_date="2026-06-01",
            amount=Decimal("5.00"),
            currency=self.usd,
            description="Bob secret",
        )
        response = self.client.get("/api/v1/transactions/recent/")
        self.assertNotIn("Bob secret", [row["description"] for row in response.data])

    def test_stats_describes_the_ledger(self):
        response = self.client.get("/api/v1/transactions/stats/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Four with a description plus one blank.
        self.assertEqual(response.data["count"], 5)
        self.assertEqual(str(response.data["first_date"]), "2026-01-05")
        self.assertEqual(response.data["without_description"], 1)

    def test_stats_is_scoped_to_the_user(self):
        Transaction.objects.create(
            user=self.bob,
            account=self.bob_account,
            transaction_type=Transaction.Type.EXPENSE,
            transaction_date="2026-01-05",
            amount=Decimal("5.00"),
            currency=self.usd,
        )
        response = self.client.get("/api/v1/transactions/stats/")
        self.assertEqual(response.data["count"], 5)


class TransactionOrderingTests(TransactionBaseTestCase):
    """Ordering must be deterministic, and "recently added" must beat same-date imports.

    A real ledger has many rows sharing a transaction date (an import inserts
    hundreds for the same day). Ordering by date alone leaves their relative order
    up to the database, so a row entered seconds ago could sit below rows entered
    days earlier.
    """

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.alice)
        # Three imported rows, all on the same day, entered first.
        for amount in ("10.00", "20.00", "30.00"):
            Transaction.objects.create(
                user=self.alice,
                account=self.alice_account,
                transaction_type=Transaction.Type.EXPENSE,
                transaction_date="2026-09-08",
                amount=Decimal(amount),
                currency=self.usd,
                description="imported",
            )
        self.imported_ids = list(
            Transaction.objects.filter(description="imported")
            .order_by("id")
            .values_list("id", flat=True)
        )
        # Then two rows entered now, with an *earlier* transaction date.
        for amount in ("1.00", "2.00"):
            Transaction.objects.create(
                user=self.alice,
                account=self.alice_account,
                transaction_type=Transaction.Type.EXPENSE,
                transaction_date="2026-09-01",
                amount=Decimal(amount),
                currency=self.usd,
                description="just entered",
            )

    def _ids(self, query):
        response = self.client.get(f"/api/v1/transactions/?{query}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [row["id"] for row in response.data["results"]]

    def test_recently_added_puts_new_rows_first_across_dates(self):
        ids = self._ids("ordering=-created_date,-id")
        self.assertEqual(ids[:2], list(reversed(
            Transaction.objects.filter(description="just entered")
            .order_by("id")
            .values_list("id", flat=True)
        )))

    def test_date_ordering_is_month_first(self):
        """Rows from a newer month come first, whatever order they were entered in."""
        # A row entered last, but dated in an older month.
        old_month = Transaction.objects.create(
            user=self.alice,
            account=self.alice_account,
            transaction_type=Transaction.Type.EXPENSE,
            transaction_date="2026-08-01",
            amount=Decimal("9.00"),
            currency=self.usd,
            description="entered last, dated last month",
        )
        ids = self._ids("ordering=-transaction_date")
        self.assertNotEqual(ids[0], old_month.id)
        # Every September row precedes every August row.
        months = list(
            Transaction.objects.filter(id__in=ids).values_list("id", "transaction_date")
        )
        by_id = dict(months)
        months_in_order = [by_id[pk].strftime("%Y-%m") for pk in ids]
        self.assertEqual(months_in_order, sorted(months_in_order, reverse=True))

    def test_date_ordering_breaks_ties_by_insertion_within_a_month(self):
        """Inside one month, the most recently entered row leads.

        This is the case that made the screen hard to use: a batch imported for the
        current month used to sit above rows added by hand afterwards.
        """
        ids = self._ids("ordering=-transaction_date")
        same_month = [
            pk
            for pk in ids
            if Transaction.objects.get(pk=pk).transaction_date.strftime("%Y-%m") == "2026-09"
        ]
        expected = list(
            Transaction.objects.filter(pk__in=same_month)
            .order_by("-created_date", "-id")
            .values_list("id", flat=True)
        )
        self.assertEqual(same_month, expected)
        # The two rows entered most recently lead.
        newest_two = list(
            Transaction.objects.filter(description="just entered")
            .order_by("-id")
            .values_list("id", flat=True)
        )
        self.assertEqual(ids[:2], newest_two)

    def test_no_ordering_parameter_falls_back_to_date_first(self):
        """The model default keeps newest transaction date on top, ties by insertion.

        The UI always sends an explicit `ordering`, so this only affects the shell,
        the admin and ad-hoc API calls — it should still be deterministic.
        """
        ids = self._ids("")
        expected = list(
            Transaction.objects.filter(user=self.alice)
            .order_by("-transaction_date", "-created_date", "-id")
            .values_list("id", flat=True)
        )
        self.assertEqual(ids, expected)

    def test_ordering_by_amount_is_left_alone(self):
        ids = self._ids("ordering=-amount")
        amounts = list(
            Transaction.objects.filter(id__in=ids).order_by("-amount").values_list("id", flat=True)
        )
        self.assertEqual(ids, amounts)

    def test_recently_added_and_date_orders_differ(self):
        """The two orders answer different questions, so both must work.

        `-created_date` ignores the transaction date entirely; the date order leads
        with the newest month and only then falls back to insertion time.
        """
        added_first = self._ids("ordering=-created_date,-id")[0]
        date_first = self._ids("ordering=-transaction_date")[0]

        newest_entered = (
            Transaction.objects.filter(user=self.alice).order_by("-created_date", "-id").first()
        )
        self.assertEqual(added_first, newest_entered.id)

        # Date order: newest month, then most recently entered.
        expected_date_first = (
            Transaction.objects.filter(user=self.alice)
            .annotate(month=TruncMonth("transaction_date"))
            .order_by("-month", "-created_date", "-id")
            .first()
        )
        self.assertEqual(date_first, expected_date_first.id)

        # Now a row entered *after* everything but dated in an older month: the two
        # orders must genuinely disagree, which is the whole reason both exist.
        older_month = Transaction.objects.create(
            user=self.alice,
            account=self.alice_account,
            transaction_type=Transaction.Type.EXPENSE,
            transaction_date="2026-08-01",
            amount=Decimal("7.00"),
            currency=self.usd,
            description="entered last, dated last month",
        )
        self.assertEqual(self._ids("ordering=-created_date,-id")[0], older_month.id)
        self.assertNotEqual(self._ids("ordering=-transaction_date")[0], older_month.id)

    def test_ordering_is_stable_across_pages(self):
        """A deterministic order means page 1 + page 2 have no repeats or gaps."""
        first = self._ids("ordering=-transaction_date&page_size=3&page=1")
        second = self._ids("ordering=-transaction_date&page_size=3&page=2")
        self.assertEqual(len(set(first) & set(second)), 0)
        self.assertEqual(len(first), 3)
