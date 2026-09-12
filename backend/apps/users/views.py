from django.contrib.auth.models import User
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import RegisterSerializer, UserSerializer


class RegistrationThrottle(AnonRateThrottle):
    scope = "auth"


class RegisterView(generics.CreateAPIView):
    """Create a new tenant account.

    Open to anonymous callers but rate limited, and the response deliberately does
    not include the password or a token: the client logs in explicitly afterwards.
    """

    queryset = User.objects.none()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [RegistrationThrottle]


class LoginView(TokenObtainPairView):
    """JWT login. Rate limited so credentials cannot be brute forced cheaply."""

    permission_classes = [AllowAny]
    throttle_classes = [RegistrationThrottle]


class MeView(APIView):
    """Current user profile, handy for the frontend to confirm the session."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class HealthView(APIView):
    """Unauthenticated liveness probe for uptime monitors and deployments."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        from django.db import connection

        database_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:  # pragma: no cover - depends on the environment
            database_ok = False

        payload = {"status": "ok" if database_ok else "degraded", "database": database_ok}
        return Response(payload, status=status.HTTP_200_OK if database_ok else 503)
