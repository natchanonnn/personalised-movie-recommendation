from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .cookies import clear_auth_cookies, set_access_cookie, set_auth_cookies, set_refresh_cookie
from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'register'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user_data = UserSerializer(user).data
        return Response(
            {
                "message": "User registered successfully.",
                "user": user_data,
            },
            status=status.HTTP_201_CREATED,
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """POST /v1/accounts/login/

    Same credential check as the stock view, but the access/refresh tokens
    never reach the response body -- they're set as httpOnly cookies here
    and stripped out before the JSON response goes back, so JS on the page
    (and therefore any XSS) never has a token value to read.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'
    permission_classes = (permissions.AllowAny,)
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            access = response.data.pop("access")
            refresh = response.data.pop("refresh")
            set_auth_cookies(response, access, refresh)
        return response


class CookieTokenRefreshView(TokenRefreshView):
    """POST /v1/accounts/token/refresh/

    Reads the refresh token from its own httpOnly cookie (the frontend
    never sends it directly -- it can't read the cookie's value). Rotation
    is on (see SIMPLE_JWT in settings), so every refresh issues a new
    refresh token and blacklists the one just used: a stolen refresh
    cookie stops working the first time the real user's client refreshes.
    """

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if not refresh_token:
            return Response({"detail": "No refresh token cookie."}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = self.get_serializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except (InvalidToken, TokenError):
            # InvalidToken is what TokenRefreshSerializer actually raises
            # (it wraps TokenError internally) -- catching TokenError alone
            # here would miss it and let a 500 through instead of a clean 401.
            response = Response({"detail": "Refresh token invalid or expired."}, status=status.HTTP_401_UNAUTHORIZED)
            clear_auth_cookies(response)
            return response

        response = Response({"detail": "Refreshed."})
        set_access_cookie(response, serializer.validated_data["access"])
        if "refresh" in serializer.validated_data:  # present when ROTATE_REFRESH_TOKENS is on
            set_refresh_cookie(response, serializer.validated_data["refresh"])
        return response


class MeView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH) or request.data.get("refresh")
        response = Response({"message": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
        clear_auth_cookies(response)

        if not refresh_token:
            return response

        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            # Already expired/blacklisted -- cookies are cleared either way,
            # which is the part that actually matters for logout.
            pass
        return response
