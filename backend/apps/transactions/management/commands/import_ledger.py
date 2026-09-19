"""Import a ledger CSV into accounts, categories, budgets and transactions.

Usage:
    python manage.py import_ledger real_data.csv --dry-run
    python manage.py import_ledger real_data.csv --commit --user edu

The dry run is the default: it parses and validates the whole file and prints the
plan without writing anything. Re-running the same file is a no-op because every
row carries a deterministic `import_key`.
"""

from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction

from apps.transactions.importers import (
    ImportError_,
    commit_plan,
    duplicate_report,
    parse_csv,
)
from apps.transactions.models import Transaction


class Command(BaseCommand):
    help = "Import a semicolon-delimited ledger export into accounts and transactions."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to the CSV file to import.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Parse and report only (this is also the default when --commit is absent).",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            default=False,
            help="Actually write the data. Without it nothing is modified.",
        )
        parser.add_argument(
            "--user",
            default=None,
            help="Username that will own the imported data (default: id 1).",
        )
        parser.add_argument(
            "--no-reconcile",
            action="store_true",
            default=False,
            help=(
                "Leave each account balance as the raw sum of its transactions "
                "instead of matching the CSV's closing balance."
            ),
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            default=False,
            help="Delete the user's existing transactions before importing.",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            default=False,
            help="Allow running against a user that already has transactions.",
        )
        parser.add_argument(
            "--lenient",
            action="store_true",
            default=False,
            help="Skip malformed rows instead of aborting.",
        )

    # -- presentation helpers ------------------------------------------------

    def _rule(self, title: str) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(title))
        self.stdout.write("-" * max(len(title), 40))

    def _table(self, headers, rows) -> None:
        widths = [len(str(h)) for h in headers]
        for row in rows:
            for index, cell in enumerate(row):
                widths[index] = max(widths[index], len(str(cell)))
        self.stdout.write(
            "  " + "  ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers))
        )
        for row in rows:
            self.stdout.write(
                "  " + "  ".join(str(c).ljust(widths[i]) for i, c in enumerate(row))
            )

    # -- command -------------------------------------------------------------

    def handle(self, *args, **options):
        path = Path(options["csv_path"])
        commit = options["commit"] and not options["dry_run"]

        if options["user"]:
            try:
                user = User.objects.get(username=options["user"])
            except User.DoesNotExist as exc:
                raise CommandError(f"No user named {options['user']!r}.") from exc
        else:
            user = User.objects.filter(pk=1).first()
            if user is None:
                raise CommandError("No user with id 1; pass --user explicitly.")

        self.stdout.write(self.style.MIGRATE_HEADING("Import plan"))
        self.stdout.write(f"  file      : {path.resolve()}")
        self.stdout.write(f"  owner     : {user.username} (id {user.pk})")
        self.stdout.write(f"  mode      : {'COMMIT' if commit else 'DRY RUN (nothing is written)'}")

        # --- Parse ---------------------------------------------------------
        try:
            plan = parse_csv(path, strict=not options["lenient"])
        except ImportError_ as exc:
            raise CommandError(str(exc)) from exc

        existing = Transaction.objects.filter(user=user).count()
        if existing and not (options["reset"] or options["skip_existing"]):
            raise CommandError(
                f"User '{user.username}' already has {existing} transaction(s). "
                "Pass --reset to replace them or --skip-existing to add only new rows."
            )

        self._report_source(plan)
        self._report_accounts(plan)
        self._report_anomalies(plan, options)

        # --- Write ---------------------------------------------------------
        if not commit:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING("Dry run complete. Re-run with --commit to apply.")
            )
            return

        try:
            result = commit_plan(
                plan,
                user=user,
                reconcile=not options["no_reconcile"],
                reset=options["reset"],
            )
        except ImportError_ as exc:
            raise CommandError(str(exc)) from exc

        self._report_result(result)

    def _report_source(self, plan) -> None:
        self._rule("Source contents")
        self._table(
            ["metric", "value"],
            [
                ["importable rows", len(plan.rows)],
                ["skipped rows", len(plan.skipped)],
                ["accounts", len(plan.accounts)],
                ["categories", len(plan.categories)],
                ["budgets", len(plan.budgets)],
                ["currencies", ", ".join(sorted(plan.currencies))],
                ["first transaction", min(r.date for r in plan.rows)],
                ["last transaction", max(r.date for r in plan.rows)],
                ["expenses", sum(1 for r in plan.rows if r.transaction_type == "expense")],
                ["income", sum(1 for r in plan.rows if r.transaction_type == "income")],
            ],
        )

        if plan.skipped:
            self._rule("Skipped rows")
            for line, reason in plan.skipped[:20]:
                self.stdout.write(f"  line {line}: {reason}")

    def _report_accounts(self, plan) -> None:
        self._rule("Accounts to create (one per name and currency)")
        rows = []
        for account in sorted(plan.accounts.values(), key=lambda a: (-a.transaction_count, a.name)):
            label = account.name
            # Mirror the importer: only disambiguate names used in two currencies.
            if sum(1 for a in plan.accounts.values() if a.name == account.name) > 1:
                label = f"{account.name} ({account.currency_code})"
            rows.append(
                [
                    label,
                    account.account_type,
                    account.currency_code,
                    account.transaction_count,
                    account.opening_balance,
                    account.closing_balance,
                    f"{account.first_date} .. {account.last_date}",
                ]
            )
        self._table(
            ["account", "type", "cur", "rows", "opening", "closing", "period"],
            rows,
        )

    def _report_anomalies(self, plan, options) -> None:
        duplicates = duplicate_report(plan)
        if duplicates:
            self._rule("Rows that are indistinguishable from another row")
            self.stdout.write(
                "  These share date, amount, account, category, currency and description."
            )
            self.stdout.write("  They are imported as separate transactions.")
            for signature, count in duplicates[:10]:
                when, amount, account, _currency, category, description, _budget = signature
                self.stdout.write(
                    f"  x{count}  {when}  {account}  {category}  "
                    f"{amount}  {description!r}"
                )

        if plan.warnings:
            self._rule("Notes")
            for _, message in plan.warnings:
                self.stdout.write(f"  {message}")

        if options["reset"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "  --reset: the user's existing transactions will be DELETED."
                )
            )

    def _report_result(self, result) -> None:
        self._rule("Imported")
        self._table(
            ["metric", "value"],
            [
                ["currencies created", ", ".join(result.currencies_created) or "-"],
                ["accounts created", len(result.accounts_created)],
                ["categories created", len(result.categories_created)],
                ["budgets created", ", ".join(result.budgets_created) or "-"],
                ["transactions created", result.transactions_created],
                ["transactions already present", result.transactions_skipped_existing],
                ["balances reconciled", "yes" if result.reconciled else "no"],
            ],
        )

        if result.accounts_created:
            self.stdout.write("")
            for name in result.accounts_created:
                self.stdout.write(f"  + account {name}")

        if result.adjustments:
            self._rule("Balance reconciliation")
            self.stdout.write(
                "  Each difference between the transaction sum and the CSV's closing"
            )
            self.stdout.write("  balance is applied as an explicit adjustment.")
            self._table(
                ["account", "transaction sum", "csv closing balance"],
                [
                    [name, before, after]
                    for name, before, after in result.adjustments
                ],
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Import complete."))
