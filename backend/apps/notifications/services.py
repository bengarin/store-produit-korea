"""
E-mails transactionnels (texte brut : aucun HTML, donc aucune injection possible dans le message).

Configuration UNIQUEMENT par variables d'environnement (rien n'est inventé) : EMAIL_HOST, EMAIL_PORT,
EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS / EMAIL_USE_SSL, DEFAULT_FROM_EMAIL,
ORDER_NOTIFICATION_EMAILS (destinataires des alertes « nouvelle commande »).
Tant que EMAIL_HOST ou DEFAULT_FROM_EMAIL manque : chaque e-mail est journalisé « non envoyé », rien ne part.

Envoi après validation de la transaction (on_commit) ; un échec n'annule jamais la commande et est retenté
par `python manage.py send_pending_emails` (à lancer régulièrement, ex. toutes les 10 minutes).
"""

import logging

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.db import transaction
from django.utils import timezone

from .models import EmailLog

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5
STATUS_MESSAGES = {
    "confirmed": "Votre commande est confirmée. Nous préparons votre colis.",
    "shipped": "Votre commande a été expédiée. Vous paierez à la réception.",
    "delivered": "Votre commande a été livrée. Merci pour votre confiance !",
    "cancelled": "Votre commande a été annulée.",
}


def configured() -> bool:
    return bool(settings.EMAIL_HOST and settings.DEFAULT_FROM_EMAIL)


def _money(value) -> str:
    return f"{value:.2f} DH"


def _order_lines(order) -> str:
    lines = []
    for item in order.items.all():
        title = f" ({item.variant_title})" if item.variant_title and item.variant_title != "Par défaut" else ""
        lines.append(f"- {item.quantity} × {item.product_name}{title} : {_money(item.line_total)}")
    lines.append(f"Livraison : {_money(order.shipping_fee) if order.shipping_fee else 'offerte'}")
    if order.discount_total:
        lines.append(f"Remise : −{_money(order.discount_total)}")
    lines.append(f"Total à payer à la livraison : {_money(order.total)}")
    return "\n".join(lines)


def queue(kind, to, subject, body, order=None) -> EmailLog:
    """Journalise puis envoie après la transaction (si l'e-mail est configuré)."""
    recipients = [a for a in to if a]
    if not recipients:
        return None
    log = EmailLog.objects.create(
        kind=kind,
        to=", ".join(recipients),
        subject=subject[:200],
        body=body,
        order=order,
        status=EmailLog.Status.PENDING if configured() else EmailLog.Status.SKIPPED,
    )
    if log.status == EmailLog.Status.PENDING:
        transaction.on_commit(lambda: send(log.pk))
    return log


def send(log_id: int) -> bool:
    log = EmailLog.objects.filter(pk=log_id, status__in=[EmailLog.Status.PENDING, EmailLog.Status.FAILED]).first()
    if log is None or not configured():
        return False
    log.attempts += 1
    try:
        connection = get_connection(timeout=settings.EMAIL_TIMEOUT)
        EmailMessage(
            log.subject, log.body, settings.DEFAULT_FROM_EMAIL, log.to.split(", "), connection=connection
        ).send()
        log.status, log.sent_at, log.error = EmailLog.Status.SENT, timezone.now(), ""
    except Exception as exc:  # noqa: BLE001 - tout échec réseau/SMTP est journalisé, jamais propagé
        logger.warning("Échec d'envoi d'e-mail %s : %s", log.pk, exc.__class__.__name__)
        log.status, log.error = EmailLog.Status.FAILED, f"{exc.__class__.__name__}: {exc}"[:300]
    log.save(update_fields=["status", "attempts", "error", "sent_at"])
    return log.status == EmailLog.Status.SENT


def retry_pending() -> int:
    sent = 0
    for log in EmailLog.objects.filter(
        status__in=[EmailLog.Status.PENDING, EmailLog.Status.FAILED], attempts__lt=MAX_ATTEMPTS
    ):
        sent += send(log.pk)
    return sent


# --- Déclencheurs -----------------------------------------------------------------------------
def order_created(order):
    brand = settings.SITE_NAME
    queue(
        EmailLog.Kind.ORDER_ADMIN,
        settings.ORDER_NOTIFICATION_EMAILS,
        f"Nouvelle commande {order.number} — {_money(order.total)}",
        f"Nouvelle commande {order.number} ({order.ship_city_label}).\n\n{_order_lines(order)}\n\n"
        f"Détail et coordonnées dans l'administration.",
        order=order,
    )
    email = order.customer.email
    if email:  # le formulaire actuel ne demande pas d'e-mail : envoyé seulement si le client en a un
        queue(
            EmailLog.Kind.ORDER_CUSTOMER,
            [email],
            f"{brand} — commande {order.number} reçue",
            f"Bonjour {order.ship_full_name},\n\nNous avons bien reçu votre commande {order.number}.\n"
            f"Nous vous appellerons pour la confirmer.\n\n{_order_lines(order)}\n\nPaiement à la livraison.\n{brand}",
            order=order,
        )


def order_status_changed(order, status):
    email = order.customer.email
    message = STATUS_MESSAGES.get(status)
    if email and message:
        queue(
            EmailLog.Kind.STATUS_CUSTOMER,
            [email],
            f"{settings.SITE_NAME} — commande {order.number}",
            f"Bonjour {order.ship_full_name},\n\n{message}\n\nCommande {order.number} — total {_money(order.total)}.\n"
            f"{settings.SITE_NAME}",
            order=order,
        )
