# pyrefly: ignore-errors
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()


class AuthenticationTests(APITestCase):
    # pyrefly: ignore [bad-override-mutable-attribute]
    client: APIClient

    def setUp(self):
        self.register_url = reverse("register")
        self.login_url = reverse("login")
        self.logout_url = reverse("logout")
        self.user_data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
        }

    def test_registration_success(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["username"], "testuser")
        self.assertEqual(response.data["user"]["email"], "testuser@example.com")
        self.assertNotIn("password", response.data["user"])

    def test_registration_password_mismatch(self):
        data = self.user_data.copy()
        data["password_confirm"] = "DifferentPassword123!"
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_email_already_exists(self):
        User.objects.create_user(
            username="anotheruser",
            email="testuser@example.com",
            password="SomePassword123!",
        )
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_login_success(self):
        User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="SecurePassword123!",
        )
        login_data = {
            "username": "testuser",
            "password": "SecurePassword123!",
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["username"], "testuser")

    def test_login_invalid_credentials(self):
        User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="SecurePassword123!",
        )
        login_data = {
            "username": "testuser",
            "password": "WrongPassword123!",
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_success(self):
        User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="SecurePassword123!",
        )
        # Login to get refresh token
        login_data = {
            "username": "testuser",
            "password": "SecurePassword123!",
        }
        login_response = self.client.post(self.login_url, login_data)
        access_token = login_response.data["access"]
        refresh_token = login_response.data["refresh"]

        # Authenticate request
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Logout
        response = self.client.post(self.logout_url, {"refresh": refresh_token})
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        # Attempt to use the blacklisted refresh token to refresh access token
        refresh_url = reverse("token_refresh")
        refresh_response = self.client.post(refresh_url, {"refresh": refresh_token})
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_invalid_token(self):
        User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="SecurePassword123!",
        )
        login_data = {
            "username": "testuser",
            "password": "SecurePassword123!",
        }
        login_response = self.client.post(self.login_url, login_data)
        access_token = login_response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Post invalid refresh token
        response = self.client.post(self.logout_url, {"refresh": "invalidtoken"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
