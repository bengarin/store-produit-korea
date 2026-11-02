"""
Double authentification (2FA) — implémentation standard django-otp :
- TOTP (RFC 6238, codes à 6 chiffres toutes les 30 s) : Google Authenticator, Microsoft Authenticator, Aegis… ;
- 10 codes de secours à usage unique (StaticDevice), affichés UNE seule fois ;
- django-otp ralentit automatiquement les essais après chaque erreur (ThrottlingMixin).

États d'un utilisateur connecté (`status(request)`) :
- "verified"       : 2FA validée pour cette session (ou non exigée et non activée) → accès normal ;
- "required"       : 2FA activée, code pas encore saisi → seules les routes 2FA / me / logout répondent ;
- "setup_required" : 2FA obligatoire pour son rôle (TWO_FACTOR_REQUIRED_ROLES) mais pas encore activée.
"""

import secrets

from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone
from django_otp import devices_for_user, user_has_device
from django_otp import login as otp_login
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

BACKUP_CODES = 10


def required_for(user) -> bool:
    roles = set(getattr(settings, "TWO_FACTOR_REQUIRED_ROLES", []))
    return bool(user.role and user.role.value in roles)


def enabled(user) -> bool:
    return user_has_device(user, confirmed=True)


def status(request) -> str:
    user = request.user
    if enabled(user):
        # is_verified est posé par OTPMiddleware (absent juste après login() dans la même requête).
        return "verified" if getattr(user, "is_verified", lambda: False)() else "required"
    return "setup_required" if required_for(user) else "verified"


def payload(request) -> dict:
    user = request.user
    return {
        "enabled": enabled(user),
        "required": required_for(user),
        "status": status(request),
        "backupCodesLeft": StaticToken.objects.filter(device__user=user, device__confirmed=True).count(),
    }


def start_setup(user) -> dict:
    """Nouvel appareil TOTP NON confirmé (remplace un essai précédent). Retourne l'URI et le QR code (image SVG)."""
    import segno

    TOTPDevice.objects.filter(user=user, confirmed=False).delete()
    device = TOTPDevice.objects.create(user=user, name="Application d'authentification", confirmed=False)
    uri = device.config_url  # émetteur : réglage OTP_TOTP_ISSUER
    qr = segno.make(uri, error="m")
    return {
        "otpauthUri": uri,
        # Image SVG complète (avec xmlns) en data URI : affichée telle quelle dans une balise <img>.
        "qrDataUri": qr.svg_data_uri(scale=5, dark="#17382d", light="#ffffff", border=2),
        # Saisie manuelle (base32) si le QR code ne peut pas être scanné.
        "secret": _base32(device.bin_key),
    }


def _base32(key: bytes) -> str:
    import base64

    return base64.b32encode(key).decode().rstrip("=")


def confirm_setup(request, code: str) -> list[str] | None:
    """Valide le premier code ; active la 2FA, crée les codes de secours (renvoyés une seule fois)."""
    user = request.user
    device = TOTPDevice.objects.filter(user=user, confirmed=False).order_by("-id").first()
    if device is None or not device.verify_token(code):
        return None
    TOTPDevice.objects.filter(user=user, confirmed=True).delete()
    device.confirmed = True
    device.save(update_fields=["confirmed"])
    codes = regenerate_backup_codes(user)
    otp_login(request, device)
    return codes


def regenerate_backup_codes(user) -> list[str]:
    StaticDevice.objects.filter(user=user).delete()
    static = StaticDevice.objects.create(user=user, name="Codes de secours", confirmed=True)
    codes = [f"{secrets.randbelow(10**8):08d}" for _ in range(BACKUP_CODES)]
    StaticToken.objects.bulk_create([StaticToken(device=static, token=c) for c in codes])
    return codes


def verify(request, code: str) -> bool:
    """Code TOTP ou code de secours (consommé). Réussite → session vérifiée."""
    code = "".join(code.split())
    for device in devices_for_user(request.user, confirmed=True):
        if device.verify_token(code):
            otp_login(request, device)
            return True
    return False


def disable(user):
    for device in devices_for_user(user, confirmed=None):
        device.delete()


def revoke_sessions(user, keep_session_key: str | None = None) -> int:
    """Ferme toutes les sessions de l'utilisateur (sauf, éventuellement, la session en cours)."""
    count = 0
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        if session.session_key == keep_session_key:
            continue
        if session.get_decoded().get("_auth_user_id") == str(user.pk):
            session.delete()
            count += 1
    return count
