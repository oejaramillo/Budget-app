"""Currency catalogue, conversion and access-control tests."""

from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Currency


class CurrencyModelTests(APITestCase):
    def setUp(self):
        self.usd = Currency.objects.create(
            code="USD", name="US Dollar", exchange_rate=Decimal("1"), principal=True
        )
        self.eur = Currency.objects.create(
            code="EUR", name="Euro", exchange_rate=Decimal("0.8")
        )

    def test_conversion_uses_decimal_arithmetic(self):
        # 100 USD -> EUR at 0.8 EUR per USD
        self.assertEqual(self.usd.convert_to(Decimal("100"), self.eur), Decimal("80.00"))

    def test_conversion_back_to_base(self):
        # 80 EUR -> USD at 1/0.8
        self.assertEqual(self.eur.convert_to(Decimal("80"), self.usd), Decimal("100.00"))

    def test_same_currency_is_identity(self):
        self.assertEqual(self.usd.convert_to(Decimal("12.34"), self.usd), Decimal("12.34"))

    def test_conversion_rejects_float(self):
        with self.assertRaises(TypeError):
            self.usd.convert_to(100.0, self.eur)

    def test_only_one_principal_currency_is_allowed(self):
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Currency.objects.create(
                    code="GBP", name="Pound", exchange_rate=Decimal("0.75"), principal=True
                )

    def test_principal_helper_returns_single_row(self):
        self.assertEqual(Currency.principal_currency(), self.usd)


class CurrencyAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="pw-not-used-1234")
        self.staff = User.objects.create_user(
            username="admin", password="pw-not-used-1234", is_staff=True
        )
        self.usd = Currency.objects.create(
            code="USD", name="US Dollar", exchange_rate=Decimal("1"), principal=True
        )
        self.eur = Currency.objects.create(
            code="EUR", name="Euro", exchange_rate=Decimal("0.9")
        )

    def test_list_requires_authentication(self):
        self.assertEqual(
            self.client.get("/api/v1/currencies/").status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_regular_user_can_read_the_catalogue(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/currencies/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        codes = {row["code"] for row in response.data["results"]}
        self.assertEqual(codes, {"USD", "EUR"})

    def test_regular_user_cannot_create_currencies(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/currencies/",
            {"code": "JPY", "name": "Yen", "exchange_rate": "150"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_can_create_currencies(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            "/api/v1/currencies/",
            {"code": "jpy", "name": "Yen", "exchange_rate": "150"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Codes are normalised to uppercase.
        self.assertEqual(response.data["code"], "JPY")

    def test_convert_endpoint(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            f"/api/v1/currencies/{self.usd.pk}/convert/?target=EUR&amount=200"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(response.data["converted_amount"])), Decimal("180.00"))

    def test_convert_rejects_unknown_target(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            f"/api/v1/currencies/{self.usd.pk}/convert/?target=XXX&amount=200"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rate_validation_rejects_zero(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            "/api/v1/currencies/",
            {"code": "ZWL", "name": "Zero", "exchange_rate": "0"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
