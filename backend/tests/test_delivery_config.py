"""Configuration de livraison (Admin → Réglages) : gratuite / payante / par zone, calculée par le serveur."""

from decimal import Decimal

import pytest

from apps.accounts.roles import Role
from apps.orders.models import Order
from apps.store_settings.models import StoreSettings
from tests.conftest import order_payload, post_order

SETTINGS = "/api/v1/admin/settings"


@pytest.fixture
def configure(staff):
    admin = staff(Role.ADMIN)  # un seul compte admin par test
    return lambda **data: admin.patch(SETTINGS, data, format="json")


@pytest.mark.django_db
def test_par_defaut_tarif_de_la_zone_aucun_montant_invente(client, sellable):
    sellable(stock=5)
    s = StoreSettings.load()
    assert s.delivery_mode == "zones" and s.delivery_fee is None
    cfg = client.get("/api/v1/store/config").json()
    assert cfg["deliveryMode"] == "zones" and cfg["deliveryFee"] == 20  # tarif de la zone (inchangé)
    assert post_order(client, order_payload([("creme-test", 1)])).json()["totals"]["delivery"] == 20


@pytest.mark.django_db
def test_livraison_gratuite(client, configure, sellable):
    sellable(stock=5)
    r = configure(deliveryMode="free")
    assert r.status_code == 200 and r.json()["deliveryMode"] == "free"
    cfg = client.get("/api/v1/store/config").json()
    assert cfg["deliveryFee"] == 0 and cfg["freeDeliveryThreshold"] is None
    totals = post_order(client, order_payload([("creme-test", 2)])).json()["totals"]
    assert totals["delivery"] == 0 and totals["total"] == 258
    assert Order.objects.get().shipping_fee == Decimal("0.00")


@pytest.mark.django_db
def test_livraison_payante_montant_configure(client, configure, sellable):
    sellable(stock=5)
    assert configure(deliveryMode="paid", deliveryFee="35.50").status_code == 200
    assert client.get("/api/v1/store/config").json()["deliveryFee"] == 35.5
    payload = order_payload([("creme-test", 1)])
    payload["totals"] = {"delivery": 0, "total": 1}  # navigateur malveillant : ignoré
    totals = post_order(client, payload).json()["totals"]
    assert totals["delivery"] == 35.5 and totals["total"] == 164.5


@pytest.mark.django_db
def test_mode_payant_exige_un_montant(configure, shop):
    for data in ({"deliveryMode": "paid"}, {"deliveryMode": "paid", "deliveryFee": "0"}, {"deliveryFee": "-5"}):
        r = configure(**data)
        assert r.status_code == 400, data
    assert StoreSettings.load().delivery_mode == "zones"  # rien n'a changé


@pytest.mark.django_db
def test_commandes_historiques_gardent_leurs_frais(client, configure, sellable):
    sellable(stock=5)
    post_order(client, order_payload([("creme-test", 1)]))
    configure(deliveryMode="paid", deliveryFee="50")
    post_order(client, order_payload([("creme-test", 1)], phone="0698765432"))
    configure(deliveryMode="free")
    assert list(Order.objects.order_by("id").values_list("shipping_fee", flat=True)) == [
        Decimal("20.00"),
        Decimal("50.00"),
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.ORDER_MANAGER, Role.CONTENT_EDITOR, Role.ANALYST])
def test_seuls_proprietaire_et_admin_modifient(staff, shop, role):
    r = staff(role).patch(SETTINGS, {"deliveryMode": "free"}, format="json")
    assert r.status_code == 403
    assert StoreSettings.load().delivery_mode == "zones"


@pytest.mark.django_db
def test_modification_journalisee(configure, shop):
    from apps.audit.models import AuditLog

    configure(deliveryMode="paid", deliveryFee="30")
    log = AuditLog.objects.filter(action="settings.update").latest("id")
    assert "delivery_mode" in str(log.changes) and "30" in str(log.changes)
