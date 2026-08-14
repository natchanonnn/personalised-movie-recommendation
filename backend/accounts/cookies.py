from django.conf import settings
from rest_framework_simplejwt.settings import api_settings as jwt_settings


def set_access_cookie(response, access_token: str) -> None:
    response.set_cookie(
        settings.AUTH_COOKIE_ACCESS,
        access_token,
        max_age=int(jwt_settings.ACCESS_TOKEN_LIFETIME.total_seconds()),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path="/",
    )


def set_refresh_cookie(response, refresh_token: str) -> None:
    response.set_cookie(
        settings.AUTH_COOKIE_REFRESH,
        refresh_token,
        max_age=int(jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        # Only the refresh endpoint needs this cookie -- scoping the path
        # means it isn't replayed on every other request.
        path="/v1/accounts/token/refresh/",
    )


def set_logged_in_marker(response, max_age: int) -> None:
    # Non-sensitive: just lets the frontend know "you have a session" so it
    # can render logged-in UI on first paint without an extra /me round
    # trip. Carries no token material, so it's fine for JS to read it.
    response.set_cookie(
        "logged_in",
        "1",
        max_age=max_age,
        httponly=False,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path="/",
    )


def set_auth_cookies(response, access_token: str, refresh_token: str) -> None:
    set_access_cookie(response, access_token)
    set_refresh_cookie(response, refresh_token)
    set_logged_in_marker(response, max_age=int(jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds()))


def clear_auth_cookies(response) -> None:
    response.delete_cookie(settings.AUTH_COOKIE_ACCESS, path="/")
    response.delete_cookie(settings.AUTH_COOKIE_REFRESH, path="/v1/accounts/token/refresh/")
    response.delete_cookie("logged_in", path="/")
