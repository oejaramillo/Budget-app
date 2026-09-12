"""Registration and session endpoints."""

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class RegistrationTests(APITestCase):
    url = "/api/v1/auth/register/"

    def test_registers_a_new_user(self):
        response = self.client.post(
            self.url,
            {
                "username": "alice",
                "email": "alice@example.com",
                "password": "hunter2-goose-quiet",
                "password_confirm": "hunter2-goose-quiet",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="alice").exists())
        # The password must never come back in the response.
        self.assertNotIn("password", response.data)

    def test_rejects_mismatched_passwords(self):
        response = self.client.post(
            self.url,
            {
                "username": "bob",
                "password": "hunter2-goose-quiet",
                "password_confirm": "something-else",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="bob").exists())

    def test_rejects_weak_password(self):
        response = self.client.post(
            self.url,
            {"username": "carol", "password": "12345678", "password_confirm": "12345678"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_rejects_duplicate_username_case_insensitively(self):
        User.objects.create_user(username="Dave", password="hunter2-goose-quiet")
        response = self.client.post(
            self.url,
            {
                "username": "dave",
                "password": "hunter2-goose-quiet",
                "password_confirm": "hunter2-goose-quiet",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SessionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="erin", password="hunter2-goose-quiet"
        )

    def test_login_returns_token_pair(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": "erin", "password": "hunter2-goose-quiet"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_rejects_bad_password(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": "erin", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_authentication(self):
        self.assertEqual(
            self.client.get("/api/v1/auth/me/").status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_me_returns_current_user(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "erin")
        # The client needs both flags to decide whether to offer the superuser
        # console; the server still enforces access on /api/v1/ops/.
        self.assertIn("is_staff", response.data)
        self.assertIn("is_superuser", response.data)
        self.assertFalse(response.data["is_superuser"])

    def test_me_reports_superuser_status(self):
        root = User.objects.create_superuser(
            username="root", email="root@example.com", password="root-password-123"
        )
        self.client.force_authenticate(root)
        response = self.client.get("/api/v1/auth/me/")
        self.assertTrue(response.data["is_superuser"])
        self.assertTrue(response.data["is_staff"])

    def test_health_is_public(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["database"])
