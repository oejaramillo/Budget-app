"""Superuser console: permission gates, operation dispatch, checks and tenant admin."""

import json
from decimal import Decimal
from unittest import mock

from django.core.serializers.json import DjangoJSONEncoder

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from apps.accounts.models import Account
from apps.currencies.models import Currency
from apps.transactions.models import Category, Transaction

from .models import OperationRun, OpsSettings
from .views import TenantViewSet
from . import services


class OpsBaseTestCase(APITestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="root", email="root@example.com", password="root-password-123"
        )
        self.staff = User.objects.create_user(
            username="staff", password="staff-password-123", is_staff=True
        )
        self.alice = User.objects.create_user(username="alice", password="alice-password-123")
        self.usd = Currency.objects.create(
            code="USD", name="US Dollar", exchange_rate=Decimal("1"), principal=True
        )


class OpsPermissionTests(OpsBaseTestCase):
    """The console is superuser-only; `is_staff` is not enough."""

    def test_anonymous_is_rejected(self):
        for path in ("/api/v1/ops/overview/", "/api/v1/ops/operations/", "/api/v1/ops/tenants/"):
            self.assertEqual(self.client.get(path).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_is_rejected(self):
        self.client.force_authenticate(self.alice)
        for path in ("/api/v1/ops/overview/", "/api/v1/ops/operations/", "/api/v1/ops/tenants/"):
            self.assertEqual(self.client.get(path).status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_without_superuser_is_rejected(self):
        """`is_staff` opens the Django admin, not the maintenance console."""
        self.client.force_authenticate(self.staff)
        self.assertEqual(
            self.client.get("/api/v1/ops/overview/").status_code, status.HTTP_403_FORBIDDEN
        )
        self.assertEqual(
            self.client.post("/api/v1/ops/operations/integrity_check/run/", {}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_superuser_can_read_the_overview(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.get("/api/v1/ops/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in ("stats", "integrity", "rates", "operations", "apps", "settings"):
            self.assertIn(key, response.data)
        self.assertEqual(response.data["stats"]["totals"]["users"], 3)


class OperationRegistryTests(APITestCase):
    def test_registry_exposes_declared_fields(self):
        spec = services.get_operation("refresh_currencies")
        self.assertIsNotNone(spec)
        names = [f.name for f in spec.fields]
        self.assertEqual(names, ["base", "force", "create_missing"])

    def test_unknown_operation_key_is_rejected(self):
        self.assertIsNone(services.get_operation("drop_everything"))

    def test_booleans_accept_form_style_values(self):
        spec = services.get_operation("refresh_currencies")
        cleaned = services.clean_arguments(spec, {"force": "true", "create_missing": "0"})
        self.assertIs(cleaned["force"], True)
        self.assertIs(cleaned["create_missing"], False)

    def test_unknown_arguments_are_rejected(self):
        spec = services.get_operation("refresh_currencies")
        with self.assertRaises(services.OperationError):
            services.clean_arguments(spec, {"base": "EUR", "--shell-injection": "rm -rf /"})

    def test_required_field_is_enforced(self):
        from .services import FieldSpec, OperationSpec, Safety

        spec = OperationSpec(
            key="needs_arg",
            label="Needs an argument",
            description="",
            safety=Safety.READ,
            handler=lambda **_: {},
            fields=(FieldSpec(name="target", label="Target", required=True),),
        )
        with self.assertRaises(services.OperationError):
            services.clean_arguments(spec, {})


class SafetyPolicyTests(OpsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.superuser)

    def test_destructive_operation_is_blocked_by_default(self):
        response = self.client.post("/api/v1/ops/operations/run_migrations/run/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("disabled", response.data["detail"].lower())

    def test_mutating_operations_can_be_disabled(self):
        OpsSettings.objects.update_or_create(
            pk=1, defaults={"allow_mutating_operations": False}
        )
        response = self.client.post(
            "/api/v1/ops/operations/refresh_currencies/run/", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_read_only_operations_always_run(self):
        OpsSettings.objects.update_or_create(
            pk=1,
            defaults={"allow_mutating_operations": False, "allow_destructive_operations": False},
        )
        response = self.client.post(
            "/api/v1/ops/operations/integrity_check/run/", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_settings_endpoint_updates_switches(self):
        response = self.client.patch(
            "/api/v1/ops/settings/", {"allow_destructive_operations": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(OpsSettings.load().allow_destructive_operations)

    def test_registry_marks_blocked_operations(self):
        response = self.client.get("/api/v1/ops/operations/")
        by_key = {item["key"]: item for item in response.data}
        self.assertFalse(by_key["run_migrations"]["allowed"])
        self.assertTrue(by_key["run_migrations"]["blocked_reason"])
        self.assertTrue(by_key["integrity_check"]["allowed"])


class OperationDispatchTests(OpsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.superuser)

    def test_run_is_recorded_in_the_audit_trail(self):
        response = self.client.post(
            "/api/v1/ops/operations/system_stats/run/", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], OperationRun.Status.SUCCESS)
        self.assertEqual(response.data["triggered_by"], self.superuser.pk)
        self.assertIsNotNone(response.data["duration_ms"])
        self.assertEqual(OperationRun.objects.count(), 1)

    def test_history_is_newest_first(self):
        self.client.post("/api/v1/ops/operations/system_stats/run/", {}, format="json")
        self.client.post("/api/v1/ops/operations/integrity_check/run/", {}, format="json")
        response = self.client.get("/api/v1/ops/operations/history/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["operation"], "integrity_check")

    def test_history_can_be_filtered(self):
        self.client.post("/api/v1/ops/operations/system_stats/run/", {}, format="json")
        self.client.post("/api/v1/ops/operations/integrity_check/run/", {}, format="json")
        response = self.client.get("/api/v1/ops/operations/history/?operation=system_stats")
        self.assertEqual(len(response.data), 1)

    def test_unknown_operation_returns_404(self):
        response = self.client.post("/api/v1/ops/operations/drop_everything/run/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_failure_is_recorded_and_reported(self):
        """A failing operation must leave an audit row, not just a 500."""
        spec = services.get_operation("system_stats")

        def boom(**_):
            raise services.OperationError("provider exploded")

        broken = services.OperationSpec(
            key="broken_op",
            label="Broken",
            description="",
            safety=services.Safety.READ,
            handler=boom,
        )
        with self.assertRaises(services.OperationError):
            services.execute_operation(broken, {}, user=self.superuser, enforce_policy=False)
        run = OperationRun.objects.get(operation="broken_op")
        self.assertEqual(run.status, OperationRun.Status.FAILED)
        self.assertIn("provider exploded", run.error)

    def test_refresh_operation_updates_rates(self):
        """The console path and the management command share one implementation."""
        from apps.currencies.services import RefreshResult

        fake = RefreshResult(updated=["EUR"], created=["GBP"], source="test", message="2 rates")
        with mock.patch("apps.currencies.services.refresh_rates", return_value=fake) as patched:
            response = self.client.post(
                "/api/v1/ops/operations/refresh_currencies/run/",
                {"arguments": {"force": True}},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(patched.called)
        self.assertEqual(response.data["result"]["updated"], ["EUR"])
        self.assertEqual(response.data["status"], OperationRun.Status.SUCCESS)

    def test_refresh_skips_when_rates_are_fresh(self):
        Currency.objects.filter(code="USD").update(rate_updated_at=timezone.now())
        with mock.patch("apps.currencies.services.refresh_rates") as patched:
            response = self.client.post(
                "/api/v1/ops/operations/refresh_currencies/run/", {}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], OperationRun.Status.SKIPPED)
        self.assertFalse(patched.called)


class IntegrityCheckTests(OpsBaseTestCase):
    def test_clean_database_reports_only_informational_findings(self):
        result = services.check_data_integrity()
        errors = [f for f in result["findings"] if f["severity"] == "error"]
        self.assertEqual(errors, [])

    def test_detects_balance_drift(self):
        """A balance edited outside the service layer must be reported."""
        account = Account.objects.create(
            user=self.alice, name="Cash", balance=Decimal("0.00"), currency=self.usd
        )
        Transaction.objects.create(
            user=self.alice,
            account=account,
            transaction_type=Transaction.Type.INCOME,
            transaction_date=timezone.localdate(),
            amount=Decimal("100.00"),
            currency=self.usd,
        )
        # The transaction was written directly, so the cache was never updated.
        result = services.check_data_integrity()
        codes = {f["code"] for f in result["findings"]}
        self.assertIn("account_balance_mismatch", codes)

    def test_accepts_a_correct_balance(self):
        account = Account.objects.create(
            user=self.alice, name="Cash", balance=Decimal("100.00"), currency=self.usd
        )
        Transaction.objects.create(
            user=self.alice,
            account=account,
            transaction_type=Transaction.Type.INCOME,
            transaction_date=timezone.localdate(),
            amount=Decimal("100.00"),
            currency=self.usd,
        )
        result = services.check_data_integrity()
        codes = {f["code"] for f in result["findings"]}
        self.assertNotIn("account_balance_mismatch", codes)

    def test_accounts_for_incoming_transfers(self):
        # Sending 50 out of an account that started at zero leaves it at -50.
        source = Account.objects.create(
            user=self.alice, name="From", balance=Decimal("-50.00"), currency=self.usd
        )
        destination = Account.objects.create(
            user=self.alice, name="To", balance=Decimal("50.00"), currency=self.usd
        )
        Transaction.objects.create(
            user=self.alice,
            account=source,
            destination_account=destination,
            transaction_type=Transaction.Type.TRANSFER,
            transaction_date=timezone.localdate(),
            amount=Decimal("50.00"),
            currency=self.usd,
        )
        result = services.check_data_integrity()
        codes = {f["code"] for f in result["findings"]}
        self.assertNotIn("account_balance_mismatch", codes)

    def test_detects_missing_principal_currency(self):
        Currency.objects.update(principal=False)
        result = services.check_data_integrity()
        codes = {f["code"] for f in result["findings"]}
        self.assertIn("no_principal_currency", codes)

    def test_detects_foreign_currency_transaction_without_rate(self):
        eur = Currency.objects.create(code="EUR", name="Euro", exchange_rate=Decimal("0.9"))
        account = Account.objects.create(
            user=self.alice, name="Cash", balance=Decimal("0.00"), currency=self.usd
        )
        Transaction.objects.create(
            user=self.alice,
            account=account,
            transaction_type=Transaction.Type.EXPENSE,
            transaction_date=timezone.localdate(),
            amount=Decimal("10.00"),
            currency=eur,
        )
        result = services.check_data_integrity()
        codes = {f["code"] for f in result["findings"]}
        self.assertIn("foreign_currency_without_rate", codes)

    def test_detects_tenant_link_mismatch(self):
        bob = User.objects.create_user(username="bob", password="bob-password-123")
        alice_category = Category.objects.create(user=self.alice, name="Groceries")
        alice_account = Account.objects.create(
            user=self.alice, name="Cash", balance=Decimal("0.00"), currency=self.usd
        )
        Transaction.objects.create(
            user=bob,
            account=alice_account,
            category=alice_category,
            transaction_type=Transaction.Type.EXPENSE,
            transaction_date=timezone.localdate(),
            amount=Decimal("5.00"),
            currency=self.usd,
        )
        result = services.check_data_integrity()
        codes = {f["code"] for f in result["findings"]}
        self.assertIn("transaction_account_currency_mismatch", codes)


class SystemStatsTests(OpsBaseTestCase):
    def test_stats_payload_is_json_serialisable(self):
        """Regression guard: Django's SQLite backend exposes NAME as a Path.

        The overview endpoint returns these stats verbatim, so anything that cannot
        be JSON encoded is a 500 in production and invisible to a test that only
        checks individual keys.
        """
        stats = services.collect_system_stats()
        json.dumps(stats)  # raises TypeError if a Path, Decimal or date slipped in

    def test_overview_endpoint_is_json_serialisable(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.get("/api/v1/ops/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json.dumps(response.data, cls=DjangoJSONEncoder)

    def test_counts_every_tenant(self):
        Account.objects.create(
            user=self.alice, name="Cash", balance=Decimal("10.00"), currency=self.usd
        )
        stats = services.collect_system_stats()
        self.assertEqual(stats["totals"]["users"], 3)
        self.assertEqual(stats["totals"]["superusers"], 1)
        self.assertEqual(stats["totals"]["accounts"], 1)

    def test_reports_database_backend(self):
        stats = services.collect_system_stats()
        self.assertIn(stats["database"]["vendor"], {"sqlite", "postgresql"})
        self.assertIn("size_pretty", stats["database"])

    def test_rate_freshness_reports_a_fresh_currency_as_fresh(self):
        Currency.objects.filter(code="USD").update(rate_updated_at=timezone.now())
        result = services.rate_freshness(max_age_hours=1)
        self.assertFalse(result["is_stale"])
        self.assertNotIn("USD", result["stale_codes"])
        self.assertLess(result["age_hours"], 1)

    def test_rate_freshness_flags_stale_currencies(self):
        old = timezone.now() - timezone.timedelta(hours=72)
        Currency.objects.filter(code="USD").update(rate_updated_at=old)
        result = services.rate_freshness(max_age_hours=1)
        self.assertTrue(result["is_stale"])
        self.assertIn("USD", result["stale_codes"])
        self.assertGreater(result["age_hours"], 60)

    def test_currency_saved_without_a_timestamp_is_not_stale(self):
        """Creating a currency records *now* as its rate timestamp."""
        Currency.objects.create(code="EUR", name="Euro", exchange_rate=Decimal("0.9"))
        result = services.rate_freshness(max_age_hours=1)
        self.assertFalse(result["is_stale"])


class TenantAdminTests(OpsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.superuser)

    def test_lists_tenants_with_footprint(self):
        Account.objects.create(
            user=self.alice, name="Cash", balance=Decimal("10.00"), currency=self.usd
        )
        response = self.client.get("/api/v1/ops/tenants/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        alice = next(row for row in response.data["results"] if row["username"] == "alice")
        self.assertEqual(alice["account_count"], 1)

    def test_search_filters_tenants(self):
        response = self.client.get("/api/v1/ops/tenants/?search=alice")
        self.assertEqual(response.data["count"], 1)

    def test_can_deactivate_another_tenant(self):
        response = self.client.patch(
            f"/api/v1/ops/tenants/{self.alice.pk}/", {"is_active": False}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.alice.refresh_from_db()
        self.assertFalse(self.alice.is_active)

    def test_can_promote_a_tenant_to_staff(self):
        response = self.client.patch(
            f"/api/v1/ops/tenants/{self.alice.pk}/", {"is_staff": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.alice.refresh_from_db()
        self.assertTrue(self.alice.is_staff)

    def test_empty_patch_is_rejected(self):
        response = self.client.patch(
            f"/api/v1/ops/tenants/{self.alice.pk}/", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_demote_self(self):
        response = self.client.patch(
            f"/api/v1/ops/tenants/{self.superuser.pk}/", {"is_superuser": False}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_demote_the_last_superuser(self):
        """The final active superuser must survive, or nobody can administer the app.

        Reached through the guard directly: via the HTTP API the operator's own
        account is protected by the self-guard first, so this is the case that would
        otherwise only show up when a superuser edits somebody else.
        """
        view = TenantViewSet()
        # `self.superuser` is the only active superuser in this test.
        with self.assertRaises(ValidationError):
            view._guard_last_superuser(self.superuser, {"is_superuser": False})
        with self.assertRaises(ValidationError):
            view._guard_last_superuser(self.superuser, {"is_active": False})
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_superuser)

    def test_guard_allows_demotion_when_another_superuser_remains(self):
        TenantViewSet()._guard_last_superuser(self.alice, {"is_superuser": False})
        User.objects.create_superuser(
            username="root2", email="r2@example.com", password="root2-password-123"
        )
        # No exception now that a second active superuser exists.
        TenantViewSet()._guard_last_superuser(self.superuser, {"is_superuser": False})

    def test_cannot_deactivate_self(self):
        response = self.client.patch(
            f"/api/v1/ops/tenants/{self.superuser.pk}/", {"is_active": False}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)

    def test_can_demote_a_superuser_when_another_remains(self):
        other = User.objects.create_superuser(
            username="root2", email="r2@example.com", password="root2-password-123"
        )
        response = self.client.patch(
            f"/api/v1/ops/tenants/{other.pk}/", {"is_superuser": False}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        other.refresh_from_db()
        self.assertFalse(other.is_superuser)

    def test_password_reset_uses_django_validators(self):
        url = f"/api/v1/ops/tenants/{self.alice.pk}/set-password/"
        weak = self.client.post(url, {"new_password": "1234"}, format="json")
        self.assertEqual(weak.status_code, status.HTTP_400_BAD_REQUEST)

        ok = self.client.post(url, {"new_password": "brand-new-password-987"}, format="json")
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.alice.refresh_from_db()
        self.assertTrue(self.alice.check_password("brand-new-password-987"))

    def test_delete_requires_the_username_to_be_typed(self):
        url = f"/api/v1/ops/tenants/{self.alice.pk}/"
        wrong = self.client.delete(url, {"confirm_username": "not-alice"}, format="json")
        self.assertEqual(wrong.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(User.objects.filter(pk=self.alice.pk).exists())

    def test_delete_removes_the_tenant_and_their_data(self):
        account = Account.objects.create(
            user=self.alice, name="Cash", balance=Decimal("10.00"), currency=self.usd
        )
        response = self.client.delete(
            f"/api/v1/ops/tenants/{self.alice.pk}/",
            {"confirm_username": "alice"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(pk=self.alice.pk).exists())
        # Cascade removes the tenant's accounts.
        self.assertFalse(Account.objects.filter(pk=account.pk).exists())

    def test_cannot_delete_self(self):
        response = self.client.delete(
            f"/api/v1/ops/tenants/{self.superuser.pk}/",
            {"confirm_username": "root"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_summary_reports_counts(self):
        response = self.client.get("/api/v1/ops/tenants/summary/")
        self.assertEqual(response.data["total"], 3)
        self.assertEqual(response.data["superusers"], 1)
        # `create_superuser` also sets is_staff, so the superuser and the staff
        # account both count.
        self.assertEqual(response.data["staff"], 2)

    def test_profiles_cannot_be_edited_through_the_console(self):
        """Profile fields belong to the user's own /auth/me/ endpoint."""
        response = self.client.patch(
            f"/api/v1/ops/tenants/{self.alice.pk}/", {"email": "hacked@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
