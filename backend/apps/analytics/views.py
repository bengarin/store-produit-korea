import datetime as dt

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.catalog.permissions import ORDERS_PERMISSION

from . import services
from .exports import report_workbook
from .periods import MAX_DAYS, PRESETS, resolve


def _parse(value, name):
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({name: ["Date attendue au format AAAA-MM-JJ."]}) from exc


def read_params(params):
    """?preset=today|7d|30d|90d|month|last_month|year|custom (&from&to pour custom) &granularity=day|week|month"""
    preset = params.get("preset") or ("custom" if params.get("from") else "30d")
    if preset not in PRESETS:
        raise ValidationError({"preset": [f"Valeurs possibles : {', '.join(PRESETS)}."]})
    today = timezone.localdate()
    date_from = date_to = None
    if preset == "custom":
        if not params.get("from") or not params.get("to"):
            raise ValidationError({"from": ["Indiquez les dates de début et de fin."]})
        date_from, date_to = _parse(params["from"], "from"), _parse(params["to"], "to")
        if date_from > date_to:
            raise ValidationError({"from": ["La date de début doit précéder la date de fin."]})
        if (date_to - date_from).days >= MAX_DAYS:
            raise ValidationError({"from": [f"Période limitée à {MAX_DAYS} jours."]})
    current, previous = resolve(preset, today, date_from, date_to)
    granularity = params.get("granularity") or services.auto_granularity(current)
    if granularity not in services.GRANULARITIES:
        raise ValidationError({"granularity": ["Valeurs possibles : day, week, month."]})
    return preset, current, previous, granularity


class ReportView(APIView):
    """GET /api/v1/admin/analytics/report — indicateurs, comparaison, séries, répartitions, produits, clients, stock."""

    permission_classes = [ORDERS_PERMISSION]

    def get(self, request):
        preset, current, previous, granularity = read_params(request.query_params)
        return Response({"preset": preset, **services.report(current, previous, granularity)})


class ReportExportView(APIView):
    """GET /api/v1/admin/analytics/export — même rapport, en classeur Excel (une feuille par analyse)."""

    permission_classes = [ORDERS_PERMISSION]

    def get(self, request):
        _preset, current, previous, granularity = read_params(request.query_params)
        data = services.report(current, previous, granularity)
        log_action("analytics.export", actor=request.user, request=request, changes={"period": data["period"]})
        response = HttpResponse(
            report_workbook(data), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="rapport-{current.start}-{current.end}.xlsx"'
        return response
