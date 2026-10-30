"""
Authentification de l'administration : session Django (cookie HttpOnly) + jeton CSRF.

Parcours du futur front admin :
  1. GET  /api/v1/admin/auth/csrf     → dépose le cookie CSRF
  2. POST /api/v1/admin/auth/login    (en-tête X-CSRFToken) → ouvre la session
  3. GET  /api/v1/admin/auth/me       → utilisateur + rôle
  4. POST /api/v1/admin/auth/logout
"""

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.core.exceptions import error_body

from .serializers import LoginSerializer, PasswordChangeSerializer, user_payload

INVALID_CREDENTIALS = "E-mail ou mot de passe incorrect."
LOCKED_MESSAGE = "Trop de tentatives échouées. Compte temporairement bloqué, réessayez plus tard."


def lockout_response(request, original_response=None, credentials=None, *args, **kwargs):
    """Réponse renvoyée par django-axes quand un compte/IP est verrouillé."""
    return JsonResponse(error_body("account_locked", LOCKED_MESSAGE), status=429)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


# La vue de connexion est appelée sans session : DRF ne vérifie alors pas le CSRF,
# on l'impose donc explicitement.
@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        django_request = request._request

        user = authenticate(django_request, email=email, password=serializer.validated_data["password"])

        if getattr(django_request, "axes_locked_out", False):
            log_action("auth.login_locked", changes={"email": email}, request=request)
            return Response(error_body("account_locked", LOCKED_MESSAGE), status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Même message dans tous les cas d'échec : on ne révèle pas si le compte existe.
        if user is None or user.role is None:
            reason = "bad_credentials" if user is None else "no_role"
            log_action("auth.login_failed", changes={"email": email, "reason": reason}, request=request)
            return Response(
                error_body("authentication_failed", INVALID_CREDENTIALS), status=status.HTTP_401_UNAUTHORIZED
            )

        login(django_request, user)  # nouvelle clé de session + nouveau jeton CSRF
        log_action("auth.login", actor=user, target=user, request=request)
        return Response({"user": user_payload(user), "csrfToken": get_token(django_request)})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        log_action("auth.logout", actor=user, target=user, request=request)
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response({"user": user_payload(request.user)})


class PasswordChangeView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["newPassword"])
        user.save(update_fields=["password", "updated_at"])
        update_session_auth_hash(request._request, user)  # garde cette session, invalide les autres
        log_action("auth.password_change", actor=user, target=user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)
