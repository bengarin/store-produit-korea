from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.roles import Role
from apps.core.permissions import HasRole

from . import services
from .models import EmailLog

OWNER_ADMIN = HasRole.of(Role.OWNER, Role.ADMIN)


class EmailStatusView(APIView):
    """GET : configuration (sans aucun secret) + 20 derniers e-mails. Propriétaire, Admin."""

    permission_classes = [OWNER_ADMIN]

    def get(self, request):
        return Response(
            {
                "configured": services.configured(),
                "fromEmail": settings.DEFAULT_FROM_EMAIL or None,
                "host": settings.EMAIL_HOST or None,
                "orderNotificationRecipients": len(settings.ORDER_NOTIFICATION_EMAILS),
                "items": [
                    {
                        "id": e.pk,
                        "kind": e.get_kind_display(),
                        "to": e.to,
                        "subject": e.subject,
                        "status": e.status,
                        "statusLabel": e.get_status_display(),
                        "error": e.error,
                        "createdAt": e.created_at.isoformat(),
                    }
                    for e in EmailLog.objects.all()[:20]
                ],
            }
        )


class EmailTestView(APIView):
    """POST : envoie un e-mail de test à l'adresse de la personne connectée."""

    permission_classes = [OWNER_ADMIN]

    def post(self, request):
        log = services.queue(
            EmailLog.Kind.TEST,
            [request.user.email],
            f"{settings.SITE_NAME} — e-mail de test",
            "Cet e-mail confirme que l'envoi depuis la boutique fonctionne.",
        )
        return Response({"status": log.status if log else "skipped"}, status=202)
