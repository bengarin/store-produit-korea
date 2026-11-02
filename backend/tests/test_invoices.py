"""Phase 7 — factures : émises à la livraison, numérotation continue, mentions figées, TVA seulement si configurée."""

from decimal import Decimal

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.roles import Role
from apps.orders.invoicing import vat_breakdown
from apps.orders.models import Invoice, Order
from apps.store_settings.models import StoreSettings
from tests.conftest import order_payload, post_order

DELIVER = ("confirmed", "shipped", "delivered")


def make_order(client, api, i=0, flow=DELIVER):
    number = post_order(client, order_payload([("creme-test", 1)], phone=f"06333333{i:02d}")).json()["number"]
    order = Order.objects.get(number=number)
    for s in flow:
        assert api.post(f"/api/v1/admin/orders/{order.pk}/status", {"status": s}, format="json").status_code == 200
    return order


@pytest.mark.django_db
def test_facture_emise_a_la_livraison_numerotation_continue(client, staff, sellable):
    sellable(stock=50)
    api = staff()
    year = timezone.localdate().year
    pending = make_order(client, api, 0, flow=("confirmed",))
    assert not Invoice.objects.filter(order=pending).exists()
    html = api.get(f"/api/v1/admin/orders/{pending.pk}/invoice").content.decode()
    assert "<h1>Bon de commande</h1>" in html and "<h1>Facture</h1>" not in html

    numbers = [make_order(client, api, i).invoice.number for i in range(1, 4)]
    assert numbers == [f"FAC-{year}-000001", f"FAC-{year}-000002", f"FAC-{year}-000003"]
    detail = api.get(f"/api/v1/admin/orders/{Invoice.objects.get(number=numbers[0]).order_id}").json()
    assert detail["invoiceNumber"] == numbers[0]
    assert api.get(f"/api/v1/admin/orders/{pending.pk}").json()["invoiceNumber"] is None


@pytest.mark.django_db
def test_mentions_figees_et_echappees(client, staff, sellable):
    sellable(stock=50)
    api = staff(Role.OWNER)
    r = api.patch(
        "/api/v1/admin/settings",
        {"legalName": "Ma <b>Société</b> SARL", "ice": "001234567000089", "rc": "12345", "ifNumber": "4455"},
        format="json",
    )
    assert r.status_code == 200, r.content
    order = make_order(client, api)
    api.patch(
        "/api/v1/admin/settings", {"legalName": "Nouvelle raison sociale", "ice": "009999999000011"}, format="json"
    )
    html = api.get(f"/api/v1/admin/orders/{order.pk}/invoice").content.decode()
    assert "ICE : 001234567000089" in html and "009999999000011" not in html  # facture figée à l'émission
    assert "Ma &lt;b&gt;Société&lt;/b&gt; SARL" in html and "<b>Société</b>" not in html  # échappé
    assert "TVA" not in html  # aucun taux configuré : aucune TVA supposée


@pytest.mark.django_db
def test_tva_seulement_si_configuree(client, staff, sellable):
    sellable(stock=50, price="129.00")
    api = staff(Role.OWNER)
    assert api.patch("/api/v1/admin/settings", {"vatRate": "20"}, format="json").status_code == 200
    order = make_order(client, api)
    inv = order.invoice
    assert inv.vat_rate == Decimal("20.00") and inv.total == order.total
    assert inv.total_excl_vat + inv.vat_amount == inv.total  # HT + TVA = TTC payé, au centime
    assert inv.total_excl_vat == (order.total / Decimal("1.2")).quantize(Decimal("0.01"))
    html = api.get(f"/api/v1/admin/orders/{order.pk}/invoice").content.decode()
    assert "Total HT" in html and "TVA (20 %)" in html and "Total TTC" in html
    assert vat_breakdown(Decimal("149.00"), None) == (None, None)
    assert api.patch("/api/v1/admin/settings", {"vatRate": None}, format="json").json()["vatRate"] is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field,value", [("ice", "1234"), ("ice", "ABCDEFGHIJKLMNO"), ("vatRate", "150"), ("invoicePrefix", "fa-c")]
)
def test_validation_des_mentions(staff, field, value):
    r = staff(Role.OWNER).patch("/api/v1/admin/settings", {field: value}, format="json")
    assert r.status_code == 400 and field in r.json()["error"]["fields"]


@pytest.mark.django_db
def test_mentions_manquantes_signalees_a_l_ecran(client, staff, sellable):
    sellable(stock=50)
    api = staff()
    StoreSettings.objects.update(ice="", rc="", if_number="")
    order = make_order(client, api)
    html = api.get(f"/api/v1/admin/orders/{order.pk}/invoice").content.decode()
    assert "Mentions à compléter" in html and "ice" in html.lower()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,code",
    [
        (Role.OWNER, 200),
        (Role.ADMIN, 200),
        (Role.ORDER_MANAGER, 200),
        (Role.ANALYST, 200),
        (Role.CONTENT_EDITOR, 403),
        (None, 403),
    ],
)
def test_acces_aux_factures(client, staff, sellable, role, code):
    sellable(stock=50)
    order = make_order(client, staff(Role.OWNER) if role != Role.OWNER else staff(Role.ADMIN))
    assert staff(role).get(f"/api/v1/admin/orders/{order.pk}/invoice").status_code == code


@pytest.mark.django_db
def test_rattrapage_des_factures_simulation_puis_application(client, staff, sellable):
    sellable(stock=50)
    api = staff()
    order = make_order(client, api)
    Invoice.objects.filter(order=order).delete()  # commande livrée « avant la phase 7 »
    call_command("issue_missing_invoices")
    assert not Invoice.objects.filter(order=order).exists()  # simulation : rien d'écrit
    call_command("issue_missing_invoices", apply=True)
    assert Invoice.objects.filter(order=order).exists()
