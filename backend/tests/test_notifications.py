"""Phase 7 — e-mails : rien n'est envoyé sans configuration ; un échec n'annule jamais une commande."""

import pytest
from django.core import mail
from django.core.management import call_command
from django.test import override_settings

from apps.accounts.roles import Role
from apps.customers.models import Customer
from apps.notifications.models import EmailLog
from apps.orders.models import Order
from tests.conftest import order_payload, post_order

CONFIGURED = {
    "EMAIL_HOST": "smtp.exemple.invalid",
    "DEFAULT_FROM_EMAIL": "boutique@exemple.invalid",
    "ORDER_NOTIFICATION_EMAILS": ["equipe@exemple.invalid"],
    "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
}


@pytest.mark.django_db
def test_sans_configuration_rien_ne_part(client, sellable, django_capture_on_commit_callbacks):
    sellable(stock=5)
    off = override_settings(EMAIL_HOST="", DEFAULT_FROM_EMAIL="", ORDER_NOTIFICATION_EMAILS=["equipe@exemple.invalid"])
    with off, django_capture_on_commit_callbacks(execute=True):
        assert post_order(client, order_payload([("creme-test", 1)])).status_code == 201
    assert mail.outbox == []
    assert list(EmailLog.objects.values_list("kind", "status")) == [("order_admin", "skipped")]


@pytest.mark.django_db
@override_settings(**CONFIGURED)
def test_alerte_equipe_et_suivi_client(client, staff, sellable, django_capture_on_commit_callbacks):
    sellable(stock=5)
    with django_capture_on_commit_callbacks(execute=True):
        number = post_order(client, order_payload([("creme-test", 2)], name="Salma <b>B</b>")).json()["number"]
    assert len(mail.outbox) == 1  # le client n'a pas d'e-mail : seule l'équipe est prévenue
    msg = mail.outbox[0]
    assert msg.to == ["equipe@exemple.invalid"] and number in msg.subject and "Total à payer à la livraison" in msg.body
    assert msg.content_subtype == "plain"  # texte brut : aucun HTML interprété
    order = Order.objects.get(number=number)
    Customer.objects.filter(pk=order.customer_id).update(email="client@exemple.invalid")
    with django_capture_on_commit_callbacks(execute=True):
        staff().post(f"/api/v1/admin/orders/{order.pk}/status", {"status": "confirmed"}, format="json")
    assert mail.outbox[-1].to == ["client@exemple.invalid"] and "confirmée" in mail.outbox[-1].body


@pytest.mark.django_db
def test_echec_smtp_commande_creee_puis_renvoi(client, sellable, django_capture_on_commit_callbacks):
    sellable(stock=5)
    broken = {**CONFIGURED, "EMAIL_BACKEND": "tests.test_notifications.BrokenBackend"}
    with override_settings(**broken), django_capture_on_commit_callbacks(execute=True):
        assert post_order(client, order_payload([("creme-test", 1)])).status_code == 201
    log = EmailLog.objects.get()
    assert log.status == "failed" and log.attempts == 1 and "ConnectionRefused" in log.error
    with override_settings(**CONFIGURED):
        call_command("send_pending_emails")
    log.refresh_from_db()
    assert log.status == "sent" and log.attempts == 2 and len(mail.outbox) == 1


class BrokenBackend:
    def __init__(self, *args, **kwargs):
        pass

    def send_messages(self, messages):
        raise ConnectionRefusedError("SMTP injoignable")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,code",
    [(Role.OWNER, 200), (Role.ADMIN, 200), (Role.ORDER_MANAGER, 403), (Role.CONTENT_EDITOR, 403), (Role.ANALYST, 403)],
)
def test_ecran_e_mails_sans_secret(staff, role, code):
    with override_settings(**CONFIGURED, EMAIL_HOST_PASSWORD="ne-doit-jamais-sortir"):
        r = staff(role).get("/api/v1/admin/notifications/emails")
        assert r.status_code == code
        if code == 200:
            assert r.json()["configured"] is True and "ne-doit-jamais-sortir" not in r.content.decode()
