import datetime as dt

from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.permissions import ORDERS_PERMISSION

from . import services


def _parse(value, name):
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({name: ["Date attendue au format AAAA-MM-JJ."]}) from exc


class OverviewView(APIView):
    """GET /api/v1/admin/analytics/overview?from=AAAA-MM-JJ&to=AAAA-MM-JJ (défaut : 30 derniers jours)."""

    permission_classes = [ORDERS_PERMISSION]

    def get(self, request):
        today = timezone.localdate()
        date_to = _parse(request.query_params["to"], "to") if request.query_params.get("to") else today
        date_from = (
            _parse(request.query_params["from"], "from")
            if request.query_params.get("from")
            else date_to - dt.timedelta(days=29)
        )
        if date_from > date_to:
            raise ValidationError({"from": ["La date de début doit précéder la date de fin."]})
        if (date_to - date_from).days >= services.MAX_DAYS:
            raise ValidationError({"from": [f"Période limitée à {services.MAX_DAYS} jours."]})
        return Response(services.overview(date_from, date_to))
