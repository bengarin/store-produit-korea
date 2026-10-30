"""
Point d'entrée unique pour écrire dans le journal d'audit :

    log_action("product.update", actor=request.user, target=product,
               changes={"price": [129, 139]}, request=request)
"""

from .models import AuditLog

REDACTED = "[masqué]"
# Toute clé CONTENANT l'un de ces mots est masquée (mieux vaut trop masquer que pas assez).
SENSITIVE_FRAGMENTS = ("password", "passwd", "secret", "token", "csrf", "session", "apikey", "authorization", "cookie")


def _is_sensitive(key) -> bool:
    normalized = str(key).lower().replace("_", "").replace("-", "")
    return any(fragment in normalized for fragment in SENSITIVE_FRAGMENTS)


def scrub(value):
    """Masque récursivement les valeurs sensibles (mots de passe, jetons…)."""
    if isinstance(value, dict):
        return {k: (REDACTED if _is_sensitive(k) else scrub(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrub(v) for v in value]
    return value


def _client_ip(request):
    # REMOTE_ADDR uniquement : X-Forwarded-For ne sera pris en compte qu'une fois le proxy
    # de production connu (sinon n'importe qui pourrait falsifier son IP).
    return request.META.get("REMOTE_ADDR") or None


def log_action(action, *, actor=None, target=None, target_type="", target_id="", changes=None, request=None):
    if target is not None:
        target_type = target_type or target._meta.label_lower
        target_id = target_id or str(target.pk)
    if actor is not None and not getattr(actor, "is_authenticated", False):
        actor = None
    return AuditLog.objects.create(
        actor=actor,
        actor_email=getattr(actor, "email", "") or "",
        action=action,
        target_type=target_type,
        target_id=str(target_id or ""),
        changes=scrub(changes or {}),
        ip_address=_client_ip(request) if request is not None else None,
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255] if request is not None else ""),
    )
