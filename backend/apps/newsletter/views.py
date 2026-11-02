import io

from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.catalog.permissions import NEWSLETTER_READ
from apps.core.permissions import HasRole
from apps.orders.exports import safe_text

from .models import Subscriber

NEWSLETTER_PERMISSION = HasRole.of(*NEWSLETTER_READ)


class SubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    consent = serializers.BooleanField()
    consentText = serializers.CharField(max_length=240)
    website = serializers.CharField(required=False, allow_blank=True, default="")  # champ piège

    def validate_consent(self, value):
        if value is not True:
            raise serializers.ValidationError("Le consentement est obligatoire.")
        return value

    def validate_consentText(self, value):
        if "<" in value or ">" in value:
            raise serializers.ValidationError("Texte invalide.")
        return " ".join(value.split())


class SubscribeView(APIView):
    """
    POST /api/v1/store/newsletter {email, consent: true, consentText, website}
    Réponse identique que l'adresse soit nouvelle ou déjà inscrite (aucune information divulguée).
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "newsletter"

    def post(self, request):
        s = SubscribeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if not s.validated_data["website"]:  # un robot remplit le champ piège : on répond pareil, sans enregistrer
            Subscriber.objects.get_or_create(
                email=s.validated_data["email"].strip().lower(),
                defaults={"consent_text": s.validated_data["consentText"]},
            )
        return Response({"ok": True}, status=201)


class SubscriberListView(APIView):
    """GET /api/v1/admin/newsletter/subscribers — nombre et dernières inscriptions (Propriétaire, Admin)."""

    permission_classes = [NEWSLETTER_PERMISSION]

    def get(self, request):
        qs = Subscriber.objects.all()
        return Response(
            {
                "total": qs.count(),
                "items": [{"email": s.email, "consentedAt": s.consented_at.isoformat()} for s in qs[:20]],
            }
        )


class SubscriberExportView(APIView):
    permission_classes = [NEWSLETTER_PERMISSION]

    def get(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = "Inscrits"
        ws.append(["E-mail", "Consentement le", "Texte accepté", "Origine"])
        for cell in ws[1]:
            cell.font = Font(bold=True)
        rows = Subscriber.objects.order_by("consented_at")
        for s in rows:
            ws.append(
                [
                    safe_text(s.email),
                    timezone.localtime(s.consented_at).strftime("%Y-%m-%d %H:%M"),
                    safe_text(s.consent_text),
                    s.source,
                ]
            )
        for col, width in zip("ABCD", (36, 18, 70, 12), strict=True):
            ws.column_dimensions[col].width = width
        buffer = io.BytesIO()
        wb.save(buffer)
        log_action("newsletter.export", actor=request.user, request=request, changes={"count": rows.count()})
        response = HttpResponse(
            buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="newsletter-{timezone.localdate()}.xlsx"'
        return response
