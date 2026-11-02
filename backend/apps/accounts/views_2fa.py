"""
Double authentification et sessions (routes /api/v1/admin/auth/…).

  POST 2fa/verify  {code}            code TOTP ou code de secours → session vérifiée (après le mot de passe)
  POST 2fa/setup                     QR code + clé (si 2FA inactive, ou session déjà vérifiée)
  POST 2fa/confirm {code}            active la 2FA, renvoie 10 codes de secours (une seule fois)
  POST 2fa/backup-codes {password}   nouveaux codes de secours (les anciens deviennent invalides)
  POST 2fa/disable {password, code}  désactive (refusé si la 2FA est obligatoire pour le rôle)
  POST sessions/revoke               ferme toutes les AUTRES sessions du compte
"""

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.core.exceptions import error_body
from apps.core.http import Conflict

from . import twofactor

BAD_CODE = "Code incorrect ou expiré."


class CodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=20)


class PasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=200)


class DisableSerializer(PasswordSerializer):
    code = serializers.CharField(max_length=20)


def _bad(request, action):
    log_action(action, actor=request.user, target=request.user, request=request)
    return Response(error_body("authentication_failed", BAD_CODE), status=status.HTTP_400_BAD_REQUEST)


class OtpThrottled(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"


class VerifyView(OtpThrottled):
    allow_unverified = True

    def post(self, request):
        s = CodeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if not twofactor.enabled(request.user):
            raise Conflict("La double authentification n'est pas activée sur ce compte.", "otp_not_enabled")
        if not twofactor.verify(request._request, s.validated_data["code"]):
            return _bad(request, "auth.otp_failed")
        log_action("auth.otp_verified", actor=request.user, target=request.user, request=request)
        return Response({"twoFactor": twofactor.payload(request._request)})


def _can_configure(request):
    """Configurer la 2FA : seulement si elle est inactive, ou si cette session a déjà saisi un code."""
    if twofactor.enabled(request.user) and twofactor.status(request._request) != "verified":
        raise Conflict("Saisissez d'abord votre code actuel.", "otp_required")


class SetupView(OtpThrottled):
    allow_unverified = True

    def post(self, request):
        _can_configure(request)
        return Response(twofactor.start_setup(request.user))


class ConfirmView(OtpThrottled):
    allow_unverified = True

    def post(self, request):
        _can_configure(request)
        s = CodeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        codes = twofactor.confirm_setup(request._request, "".join(s.validated_data["code"].split()))
        if codes is None:
            return _bad(request, "auth.otp_setup_failed")
        log_action("auth.otp_enabled", actor=request.user, target=request.user, request=request)
        return Response({"backupCodes": codes, "twoFactor": twofactor.payload(request._request)})


class BackupCodesView(OtpThrottled):
    def post(self, request):
        s = PasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if not request.user.check_password(s.validated_data["password"]):
            return _bad(request, "auth.otp_backup_failed")
        if not twofactor.enabled(request.user):
            raise Conflict("La double authentification n'est pas activée.", "otp_not_enabled")
        codes = twofactor.regenerate_backup_codes(request.user)
        log_action("auth.otp_backup_codes", actor=request.user, target=request.user, request=request)
        return Response({"backupCodes": codes})


class DisableView(OtpThrottled):
    def post(self, request):
        s = DisableSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if twofactor.required_for(request.user):
            raise Conflict("La double authentification est obligatoire pour votre rôle.", "otp_mandatory")
        if not request.user.check_password(s.validated_data["password"]) or not twofactor.verify(
            request._request, s.validated_data["code"]
        ):
            return _bad(request, "auth.otp_disable_failed")
        twofactor.disable(request.user)
        log_action("auth.otp_disabled", actor=request.user, target=request.user, request=request)
        return Response({"twoFactor": twofactor.payload(request._request)})


class RevokeSessionsView(APIView):
    def post(self, request):
        count = twofactor.revoke_sessions(request.user, keep_session_key=request.session.session_key)
        log_action(
            "auth.sessions_revoked", actor=request.user, target=request.user, request=request, changes={"count": count}
        )
        return Response({"revoked": count})
