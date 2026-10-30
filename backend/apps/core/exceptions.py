"""
Format d'erreur unique de l'API :

    {"error": {"code": "validation_error", "message": "…", "fields": {"email": ["…"]}}}

- `code`    : identifiant stable, lisible par le front (ne change pas avec la langue)
- `message` : phrase en français pour l'utilisateur
- `fields`  : présent uniquement pour les erreurs de validation
"""

import logging

from django.http import JsonResponse
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

MESSAGES = {
    "validation_error": "Certaines informations sont invalides.",
    "not_authenticated": "Authentification requise.",
    "authentication_failed": "Identifiants invalides.",
    "permission_denied": "Vous n'avez pas les droits pour cette action.",
    "not_found": "Ressource introuvable.",
    "method_not_allowed": "Méthode non autorisée.",
    "unsupported_media_type": "Format de requête non pris en charge.",
    "parse_error": "Requête mal formée.",
    "throttled": "Trop de requêtes. Réessayez dans quelques instants.",
    "csrf_failed": "Jeton CSRF manquant ou invalide. Rechargez la page.",
    "server_error": "Erreur interne. Réessayez plus tard.",
}


def error_body(code, message=None, fields=None):
    body = {"code": code, "message": message or MESSAGES.get(code, MESSAGES["server_error"])}
    if fields:
        body["fields"] = fields
    return {"error": body}


def _flatten(detail):
    """Transforme les ErrorDetail de DRF en simples chaînes."""
    if isinstance(detail, dict):
        return {key: _flatten(value) for key, value in detail.items()}
    if isinstance(detail, list):
        return [_flatten(item) for item in detail]
    return str(detail)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        # Exception non prévue : on journalise le détail, le client ne reçoit qu'un message générique.
        logger.exception("Erreur non gérée dans l'API", exc_info=exc)
        return Response(error_body("server_error"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if isinstance(exc, exceptions.ValidationError):
        detail = _flatten(exc.detail)
        if isinstance(detail, dict):
            non_field = detail.pop("non_field_errors", None)
            message = non_field[0] if non_field else None
            response.data = error_body("validation_error", message, detail or None)
        else:
            message = detail[0] if isinstance(detail, list) and detail else None
            response.data = error_body("validation_error", message)
        return response

    code = getattr(exc, "default_code", "error")
    if isinstance(exc, exceptions.PermissionDenied) and "CSRF" in str(exc.detail):
        code = "csrf_failed"
    custom_message = None
    if isinstance(exc, exceptions.Throttled) and exc.wait:
        custom_message = f"Trop de requêtes. Réessayez dans {int(exc.wait) + 1} s."
    response.data = error_body(code, custom_message)
    return response


# --- Vues Django (hors DRF) qui renvoient le même format -----------------
def json_404(request, exception=None):
    return JsonResponse(error_body("not_found"), status=404)


def json_500(request):
    return JsonResponse(error_body("server_error"), status=500)


def csrf_failure(request, reason=""):
    return JsonResponse(error_body("csrf_failed"), status=403)
