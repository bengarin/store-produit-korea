"""Erreurs métier fréquentes, au format commun {"error": {...}}."""

from rest_framework import status
from rest_framework.exceptions import APIException


class Conflict(APIException):
    """409 : action impossible dans l'état actuel (ex. supprimer un produit déjà commandé)."""

    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"
    default_detail = "Action impossible dans l'état actuel."

    def __init__(self, message=None, code="conflict"):
        super().__init__(message or self.default_detail, code)
        self.default_code = code
