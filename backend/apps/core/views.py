import logging

from django.conf import settings
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import error_body

logger = logging.getLogger(__name__)


class HealthView(APIView):
    """
    GET /api/v1/health — état du service et de la base MySQL.
    Public : ne révèle aucune information sensible (ni version de MySQL, ni hôte).
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            logger.exception("Health check : base de données injoignable")
            body = error_body("service_unavailable", "Base de données indisponible.")
            body.update({"status": "error", "database": "unavailable"})
            return Response(body, status=503)
        return Response({"status": "ok", "database": "ok", "version": settings.APP_VERSION})
