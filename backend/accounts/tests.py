# pyrefly: ignore-errors
from django.conf import settings
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
        self.refresh_url = reverse("token_refresh")
        self.me_url = reverse("me")
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

    def test_login_never_puts_tokens_in_the_response_body(self):
        User.objects.create_user(
            username="testuser", email="testuser@example.com", password="SecurePassword123!"
        )
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "SecurePassword123!"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["username"], "testuser")

    def test_login_sets_httponly_cookies(self):
        User.objects.create_user(
            username="testuser", email="testuser@example.com", password="SecurePassword123!"
        )
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "SecurePassword123!"}
        )

        access_cookie = response.cookies[settings.AUTH_COOKIE_ACCESS]
        refresh_cookie = response.cookies[settings.AUTH_COOKIE_REFRESH]
        marker_cookie = response.cookies["logged_in"]

        self.assertTrue(access_cookie["httponly"])
        self.assertTrue(refresh_cookie["httponly"])
        # the marker cookie carries no token material, so it's fine for JS
        # to read it -- that's the whole point of it existing.
        self.assertFalse(marker_cookie["httponly"])
        self.assertEqual(marker_cookie.value, "1")

    def test_login_invalid_credentials(self):
        User.objects.create_user(
            username="testuser", email="testuser@example.com", password="SecurePassword123!"
        )
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "WrongPassword123!"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn(settings.AUTH_COOKIE_ACCESS, response.cookies)

    def test_protected_endpoint_authenticates_via_cookie_alone(self):
        User.objects.create_user(
            username="testuser", email="testuser@example.com", password="SecurePassword123!"
        )
        self.client.post(self.login_url, {"username": "testuser", "password": "SecurePassword123!"})

        # No Authorization header set anywhere -- the test client re-sends
        # whatever cookies the login response set, same as a real browser.
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "testuser")

    def test_header_auth_still_works_for_non_browser_clients(self):
        User.objects.create_user(
            username="testuser", email="testuser@example.com", password="SecurePassword123!"
        )
        login_response = self.client.post(
            self.login_url, {"username": "testuser", "password": "SecurePassword123!"}
        )
        access_token = login_response.cookies[settings.AUTH_COOKIE_ACCESS].value

        headerless_client = APIClient()  # fresh client, no cookies carried over
        response = headerless_client.get(self.me_url, HTTP_AUTHORIZATION=f"Bearer {access_token}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_refresh_rotates_token_and_blacklists_the_old_one(self):
        User.objects.create_user(
            username="testuser", email="testuser@example.com", password="SecurePassword123!"
        )
        login_response = self.client.post(
            self.login_url, {"username": "testuser", "password": "SecurePassword123!"}
        )
        old_refresh = login_response.cookies[settings.AUTH_COOKIE_REFRESH].value

        refresh_response = self.client.post(self.refresh_url)
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        new_refresh = refresh_response.cookies[settings.AUTH_COOKIE_REFRESH].value
        self.assertNotEqual(old_refresh, new_refresh)

        # Replaying the pre-rotation refresh token must now fail -- this is
        # the actual security property rotation buys: a stolen refresh
        # cookie is only good for one use before the real client's next
        # refresh invalidates it.
        self.client.cookies[settings.AUTH_COOKIE_REFRESH] = old_refresh
        replay_response = self.client.post(self.refresh_url)
        self.assertEqual(replay_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_without_cookie_returns_401(self):
        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_clears_cookies_and_blacklists_refresh_token(self):
        User.objects.create_user(
            username="testuser", email="testuser@example.com", password="SecurePassword123!"
        )
        self.client.post(self.login_url, {"username": "testuser", "password": "SecurePassword123!"})

        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        for cookie_name in (settings.AUTH_COOKIE_ACCESS, settings.AUTH_COOKIE_REFRESH, "logged_in"):
            self.assertEqual(response.cookies[cookie_name].value, "")
            self.assertLessEqual(int(response.cookies[cookie_name]["max-age"]), 0)

        # The blacklisted refresh token can no longer mint a new access token.
        refresh_response = self.client.post(self.refresh_url)
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_a_refresh_cookie_still_clears_cookies(self):
        User.objects.create_user(
            username="testuser", email="testuser@example.com", password="SecurePassword123!"
        )
        login_response = self.client.post(
            self.login_url, {"username": "testuser", "password": "SecurePassword123!"}
        )
        access_token = login_response.cookies[settings.AUTH_COOKIE_ACCESS].value

        # Keep the access cookie (so the request is authenticated) but drop
        # the refresh cookie before logging out -- logout should still
        # succeed and clear whatever cookies exist rather than 400.
        self.client.cookies.pop(settings.AUTH_COOKIE_REFRESH, None)
        response = self.client.post(
            self.logout_url, HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
