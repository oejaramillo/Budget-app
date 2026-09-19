"""CSV ledger importer: parsing, safety rails and exact re-run behaviour."""

import tempfile
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase

from apps.accounts.models import Account
from apps.budgets.models import Budget
from apps.currencies.models import Currency
from apps.transactions.models import Category, Transaction

from .importers import (
    ImportError_,
    commit_plan,
    duplicate_report,
    make_import_key,
    parse_amount,
    parse_csv,
    parse_date,
)

HEADER = (
    "fecha;monto;categoría;cuenta;presupuesto;descripción;moneda;"
    "número de transacción;"
)


def write_csv(lines: list[str]) -> Path:
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".csv", delete=False, encoding="utf-8"
    )
    handle.write(HEADER + "\n")
    for line in lines:
        handle.write(line + "\n")
    handle.close()
    return Path(handle.name)


class AmountParsingTests(TestCase):
    def test_plain_decimal(self):
        self.assertEqual(parse_amount("23.79", 2), Decimal("23.79"))

    def test_thousands_separator_is_stripped(self):
        """The real export mixes `23.79` with `-4,800.00`."""
        self.assertEqual(parse_amount("-4,800.00", 2), Decimal("-4800.00"))
        self.assertEqual(parse_amount("198,000.00", 2), Decimal("198000.00"))

    def test_empty_amount_is_rejected(self):
        with self.assertRaises(ImportError_):
            parse_amount("", 2)

    def test_non_numeric_amount_is_rejected(self):
        with self.assertRaises(ImportError_):
            parse_amount("not-money", 2)

    def test_date_parsing(self):
        self.assertEqual(str(parse_date("05/12/2018", 2)), "2018-12-05")

    def test_bad_date_is_rejected(self):
        with self.assertRaises(ImportError_):
            parse_date("Toca 1/1/2023", 4443)


class ImportKeyTests(TestCase):
    """The key decides whether re-running an import duplicates data."""

    def test_same_row_same_key(self):
        kwargs = dict(
            ordinal=5,
            account="Efectivo",
            currency="USD",
            when=parse_date("05/12/2018", 2),
            amount=Decimal("-25.00"),
            category="Comida",
            description="",
            budget="",
        )
        self.assertEqual(make_import_key(**kwargs), make_import_key(**kwargs))

    def test_identical_rows_at_different_positions_stay_distinct(self):
        """Four real 25.00 Runpod charges on one day must not collapse into one.

        Regression guard: hashing content alone lost 46 rows of real money and made
        account balances disagree with the source file.
        """
        base = dict(
            account="IDB Federal Bank",
            currency="USD",
            when=parse_date("19/05/2025", 2),
            amount=Decimal("-25.00"),
            category="Tecnología",
            description="Runpod",
            budget="",
        )
        keys = {make_import_key(ordinal=n, **base) for n in (11, 12, 13, 14)}
        self.assertEqual(len(keys), 4)


class ParseCsvTests(TestCase):
    def test_signs_become_transaction_types(self):
        path = write_csv(
            [
                "05/12/2018;-23.79;Comida;Efectivo;;lunch;Dólar estadounidense;;",
                "05/12/2018;500.00;Salarios, compensaciones;Efectivo;;pay;Dólar estadounidense;;",
            ]
        )
        plan = parse_csv(path)
        self.assertEqual([row.transaction_type for row in plan.rows], ["expense", "income"])
        # Amounts are stored unsigned; direction lives in the type.
        self.assertEqual([row.amount for row in plan.rows], [Decimal("23.79"), Decimal("500.00")])

    def test_closing_balance_is_the_signed_sum(self):
        path = write_csv(
            [
                "05/12/2018;100.00;Inicio;Efectivo;;;Dólar estadounidense;;",
                "06/12/2018;-30.00;Comida;Efectivo;;;Dólar estadounidense;;",
                "07/12/2018;-20.00;Comida;Efectivo;;;Dólar estadounidense;;",
            ]
        )
        plan = parse_csv(path)
        account = plan.accounts[("Efectivo", "USD")]
        self.assertEqual(account.closing_balance, Decimal("50.00"))
        self.assertEqual(account.opening_balance, Decimal("100.00"))
        self.assertEqual(account.transaction_count, 3)

    def test_account_with_two_currencies_is_split(self):
        path = write_csv(
            [
                "05/12/2018;-10.00;Comida;Efectivo;;;Dólar estadounidense;;",
                "10/06/2022;-1500.00;Comida;Efectivo;;;Pesos argentinos;;",
            ]
        )
        plan = parse_csv(path)
        self.assertIn(("Efectivo", "USD"), plan.accounts)
        self.assertIn(("Efectivo", "ARS"), plan.accounts)
        self.assertTrue(any("split" in message for _, message in plan.warnings))

    def test_account_name_whitespace_is_collapsed(self):
        """The real file contains 'Produbanco ' with a trailing space."""
        path = write_csv(["05/12/2018;-10.00;Comida;Produbanco ;;;Dólar estadounidense;;"])
        plan = parse_csv(path)
        self.assertIn(("Produbanco", "USD"), plan.accounts)

    def test_lowercase_category_is_merged_into_the_canonical_spelling(self):
        path = write_csv(
            [
                "05/12/2018;-10.00;Ropa;Efectivo;;;Dólar estadounidense;;",
                "06/12/2018;-20.00;ropa;Efectivo;;;Dólar estadounidense;;",
                "07/12/2018;-30.00;Ropa;Efectivo;;;Dólar estadounidense;;",
            ]
        )
        plan = parse_csv(path)
        self.assertEqual(plan.categories, {"Ropa"})

    def test_missing_category_becomes_uncategorised(self):
        path = write_csv(["05/12/2018;-10.00;;Efectivo;;;Dólar estadounidense;;"])
        plan = parse_csv(path)
        self.assertEqual(plan.rows[0].category, "Sin categoría")

    def test_blank_trailing_row_is_skipped(self):
        path = write_csv(["05/12/2018;-10.00;Comida;Efectivo;;;Dólar estadounidense;;", ";;;;;;;"])
        plan = parse_csv(path)
        self.assertEqual(len(plan.rows), 1)
        self.assertEqual(len(plan.skipped), 1)

    def test_junk_row_without_amount_or_account_is_skipped(self):
        """The real file ends with a row whose date column holds free text."""
        path = write_csv(
            ["05/12/2018;-10.00;Comida;Efectivo;;;Dólar estadounidense;;", "Toca 1/1/2023;;;;;;"]
        )
        plan = parse_csv(path)
        self.assertEqual(len(plan.rows), 1)
        self.assertIn("without an amount or account", plan.skipped[0][1])

    def test_row_missing_an_amount_stops_the_import_even_leniently(self):
        """--lenient is for unparseable values, not for dropping money."""
        path = write_csv(["05/12/2018;;Comida;Efectivo;;;Dólar estadounidense;;"])
        with self.assertRaises(ImportError_):
            parse_csv(path)
        with self.assertRaises(ImportError_):
            parse_csv(path, strict=False)

    def test_unknown_currency_aborts_by_default(self):
        path = write_csv(["05/12/2018;-10.00;Comida;Efectivo;;;Bitcoin;;"])
        with self.assertRaises(ImportError_):
            parse_csv(path)

    def test_unknown_currency_can_be_skipped_leniently(self):
        path = write_csv(
            [
                "05/12/2018;-10.00;Comida;Efectivo;;;Bitcoin;;",
                "05/12/2018;-20.00;Comida;Efectivo;;;Dólar estadounidense;;",
            ]
        )
        plan = parse_csv(path, strict=False)
        self.assertEqual(len(plan.rows), 1)
        self.assertEqual(len(plan.skipped), 1)

    def test_reference_column_is_kept_in_the_description(self):
        """Two real rows are flagged 'sospechoso'; that note must survive."""
        path = write_csv(
            [
                "15/10/2024;-48.74;Desconocido;IDB Federal Bank;;"
                "something;Dólar estadounidense;sospechoso;"
            ]
        )
        plan = parse_csv(path)
        self.assertIn("[sospechoso]", plan.rows[0].description)

    def test_missing_column_is_reported(self):
        handle = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        handle.write("fecha;monto\n05/12/2018;-10.00\n")
        handle.close()
        with self.assertRaises(ImportError_) as ctx:
            parse_csv(Path(handle.name))
        self.assertIn("missing expected column", str(ctx.exception))

    def test_budget_summary_uses_expenses_only(self):
        path = write_csv(
            [
                "05/12/2018;-100.00;Gastos de viajes;Efectivo;Viaje;;Dólar estadounidense;;",
                "06/12/2018;-50.00;Gastos de viajes;Efectivo;Viaje;;Dólar estadounidense;;",
                "07/12/2018;30.00;Ajuste;Efectivo;Viaje;;Dólar estadounidense;;",
            ]
        )
        plan = parse_csv(path)
        self.assertEqual(plan.budgets["Viaje"], [
            parse_date("05/12/2018", 2),
            parse_date("06/12/2018", 2),
            parse_date("07/12/2018", 2),
        ])

    def test_duplicate_report_finds_field_identical_rows(self):
        path = write_csv(
            [
                "19/05/2025;-25.00;Tecnología;IDB Federal Bank;;Runpod;Dólar estadounidense;;",
                "19/05/2025;-25.00;Tecnología;IDB Federal Bank;;Runpod;Dólar estadounidense;;",
            ]
        )
        plan = parse_csv(path)
        self.assertEqual(len(plan.rows), 2)
        self.assertEqual(len(duplicate_report(plan)), 1)
        self.assertEqual(duplicate_report(plan)[0][1], 2)


class CommitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="edu", password="pw-not-used-1234", is_superuser=True
        )
        Currency.objects.create(
            code="USD", name="US Dollar", exchange_rate=Decimal("1"), principal=True
        )

    def _plan(self):
        path = write_csv(
            [
                "05/12/2018;100.00;Inicio;Efectivo;;;Dólar estadounidense;;",
                "06/12/2018;-25.50;Comida;Efectivo;;lunch;Dólar estadounidense;;",
                "07/12/2018;-10.00;Comida;Efectivo;;coffee;Dólar estadounidense;;",
                "08/12/2018;500.00;Salarios, compensaciones;Banco;;pay;Dólar estadounidense;;",
            ]
        )
        return parse_csv(path)

    def test_commit_creates_everything_and_reconciles_balances(self):
        result = commit_plan(self._plan(), user=self.user)

        self.assertEqual(result.transactions_created, 4)
        self.assertEqual(
            sorted(result.accounts_created), ["Banco", "Efectivo"]
        )
        self.assertIn("Comida", result.categories_created)
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 4)

        # The ledger is self-consistent, so the balance equals the CSV closing sum
        # and no adjustment is needed.
        self.assertEqual(result.adjustments, [])
        self.assertEqual(Account.objects.get(name="Efectivo").balance, Decimal("64.50"))
        self.assertEqual(Account.objects.get(name="Banco").balance, Decimal("500.00"))

    def test_second_import_of_the_same_file_creates_nothing(self):
        commit_plan(self._plan(), user=self.user)
        before = Transaction.objects.count()

        result = commit_plan(parse_csv(self._plan_source()), user=self.user)

        self.assertEqual(result.transactions_created, 0)
        self.assertEqual(result.transactions_skipped_existing, 4)
        self.assertEqual(Transaction.objects.count(), before)

    def _plan_source(self):
        """The same file content as `_plan`, written fresh with the same ordinals."""
        path = write_csv(
            [
                "05/12/2018;100.00;Inicio;Efectivo;;;Dólar estadounidense;;",
                "06/12/2018;-25.50;Comida;Efectivo;;lunch;Dólar estadounidense;;",
                "07/12/2018;-10.00;Comida;Efectivo;;coffee;Dólar estadounidense;;",
                "08/12/2018;500.00;Salarios, compensaciones;Banco;;pay;Dólar estadounidense;;",
            ]
        )
        return path

    def test_balances_survive_a_second_import(self):
        """Regression guard: the reconcile step used to run only when a difference existed."""
        commit_plan(self._plan(), user=self.user)
        commit_plan(parse_csv(self._plan_source()), user=self.user)

        self.assertEqual(Account.objects.get(name="Efectivo").balance, Decimal("64.50"))
        self.assertEqual(Account.objects.get(name="Banco").balance, Decimal("500.00"))

    def test_balance_adjustment_is_reported_when_the_csv_implies_more(self):
        """Capital the ledger cannot explain is reported, not smuggled in."""
        path = write_csv(["06/12/2018;-25.50;Comida;Efectivo;;lunch;Dólar estadounidense;;"])
        plan = parse_csv(path)
        # Pretend the export claims a higher closing balance than its rows support.
        plan.accounts[("Efectivo", "USD")].closing_balance = Decimal("100.00")

        result = commit_plan(plan, user=self.user)

        self.assertEqual(len(result.adjustments), 1)
        name, derived, target = result.adjustments[0]
        self.assertEqual(name, "Efectivo")
        self.assertEqual(derived, Decimal("-25.50"))
        self.assertEqual(target, Decimal("100.00"))
        self.assertEqual(Account.objects.get(name="Efectivo").balance, Decimal("100.00"))

    def test_no_reconcile_uses_the_transaction_sum(self):
        path = write_csv(["06/12/2018;-25.50;Comida;Efectivo;;lunch;Dólar estadounidense;;"])
        plan = parse_csv(path)
        plan.accounts[("Efectivo", "USD")].closing_balance = Decimal("999.00")

        result = commit_plan(plan, user=self.user, reconcile=False)

        self.assertFalse(result.reconciled)
        self.assertEqual(Account.objects.get(name="Efectivo").balance, Decimal("-25.50"))

    def test_mixed_currency_accounts_are_named_apart(self):
        path = write_csv(
            [
                "06/12/2018;-25.50;Comida;Efectivo;;;Dólar estadounidense;;",
                "10/06/2022;-1500.00;Comida;Efectivo;;;Pesos argentinos;;",
            ]
        )
        commit_plan(parse_csv(path), user=self.user)

        usd = Account.objects.get(name="Efectivo (USD)")
        ars = Account.objects.get(name="Efectivo (ARS)")
        self.assertEqual(usd.currency.code, "USD")
        self.assertEqual(ars.currency.code, "ARS")
        self.assertEqual(usd.balance, Decimal("-25.50"))
        self.assertEqual(ars.balance, Decimal("-1500.00"))

    def test_currencies_are_created_with_the_base_flag(self):
        path = write_csv(["10/06/2022;-1500.00;Comida;Efectivo;;;Pesos argentinos;;"])
        result = commit_plan(parse_csv(path), user=self.user)

        self.assertEqual(result.currencies_created, ["ARS"])
        self.assertTrue(Currency.objects.get(code="USD").principal)
        self.assertFalse(Currency.objects.get(code="ARS").principal)

    def test_budget_is_created_from_the_observed_span(self):
        path = write_csv(
            [
                "05/12/2018;-100.00;Gastos de viajes;Efectivo;Viaje Tailandia – China;;Dólar estadounidense;;",
                "20/12/2018;-60.00;Gastos de viajes;Efectivo;Viaje Tailandia – China;;Dólar estadounidense;;",
            ]
        )
        commit_plan(parse_csv(path), user=self.user)

        budget = Budget.objects.get(name="Viaje Tailandia – China")
        self.assertEqual(str(budget.start_date), "2018-12-05")
        self.assertEqual(str(budget.end_date), "2018-12-20")
        self.assertEqual(budget.max_amount, Decimal("160.00"))
        self.assertEqual(
            Transaction.objects.filter(budget=budget).count(), 2
        )

    def test_skipped_transactions_are_not_linked_to_a_missing_budget(self):
        path = write_csv(["05/12/2018;-10.00;Comida;Efectivo;;;Dólar estadounidense;;"])
        commit_plan(parse_csv(path), user=self.user)
        transaction = Transaction.objects.get()
        self.assertIsNone(transaction.budget)
        self.assertEqual(transaction.category.name, "Comida")

    def test_reset_replaces_existing_transactions(self):
        commit_plan(self._plan(), user=self.user)
        self.assertEqual(Transaction.objects.count(), 4)

        commit_plan(parse_csv(self._plan_source()), user=self.user, reset=True)

        # Deleted then re-created: still exactly one copy, never eight.
        self.assertEqual(Transaction.objects.count(), 4)
        self.assertEqual(Account.objects.get(name="Efectivo").balance, Decimal("64.50"))

    def test_large_import_does_not_trip_the_sqlite_statement_limit(self):
        """Regression guard: a fixed batch_size of 500 hit SQLite's MAX_COMPOUND_SELECT."""
        lines = [
            f"0{(index % 9) + 1}/12/2018;-1.00;Comida;Efectivo;;row {index};Dólar estadounidense;;"
            for index in range(1200)
        ]
        plan = parse_csv(write_csv(lines))
        result = commit_plan(plan, user=self.user)

        self.assertEqual(result.transactions_created, 1200)
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 1200)
