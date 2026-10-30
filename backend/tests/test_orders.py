"""Création de commande publique (paiement à la livraison) — tout est recalculé par le serveur."""

import re
from decimal import Decimal
from unittest import mock

import pytest

from apps.audit.models import AuditLog
from apps.catalog.models import Variant
from apps.customers.models import Customer
from apps.inventory.models import StockMovement
from apps.orders.models import Order
from tests.conftest import order_payload, post_order


@pytest.mark.django_db
def test_commande_complete(client, sellable):
    p = sellable(stock=10)
    payload = order_payload([("creme-test", 2)])
    payload["totals"] = {"total": 1}  # envoyé par un navigateur malveillant : IGNORÉ
    payload["items"][0]["price"] = 1
    response = post_order(client, payload)
    assert response.status_code == 201, response.content
    data = response.json()
    assert re.fullmatch(r"MPC-\d{4}-\d{6}", data["number"])
    assert data["totals"] == {"itemCount": 2, "subtotal": 258, "discount": 0, "delivery": 20, "total": 278}
    assert data["status"] == "pending" and data["items"][0]["price"] == 129
    assert "phone" not in str(data) and "Orangers" not in str(data)  # aucune donnée personnelle renvoyée

    order = Order.objects.get()
    assert order.total == Decimal("278.00") and order.payment_method == "cod"
    assert order.ship_phone == "+212612345678" and order.ship_city_label == "Casablanca"
    item = order.items.get()
    assert (item.product_name, item.unit_price, item.unit_cost, item.quantity) == (
        "Marque Crème test",
        Decimal("129.00"),
        Decimal("40.00"),
        2,
    )
    assert Variant.objects.get(product=p).stock_quantity == 8
    move = StockMovement.objects.get()
    assert (move.delta, move.quantity_before, move.quantity_after, move.reason, move.order) == (
        -2,
        10,
        8,
        "order_placed",
        order,
    )
    customer = Customer.objects.get()
    assert customer.phone == "+212612345678" and customer.orders_count == 1
    assert customer.addresses.get().address_line == "12 rue des Orangers, Maarif"
    assert order.history.get().to_status == "pending"
    assert AuditLog.objects.filter(action="order.create").exists()


@pytest.mark.django_db
def test_les_lignes_gardent_le_prix_du_moment(client, sellable):
    p = sellable()
    post_order(client, order_payload([("creme-test", 1)]))
    Variant.objects.filter(product=p).update(price=Decimal("199"))
    p.name = "Nom changé"
    p.save()
    item = Order.objects.get().items.get()
    assert item.unit_price == Decimal("129.00") and item.product_name == "Marque Crème test"


@pytest.mark.django_db
def test_stock_non_renseigne_jamais_commandable(client, sellable):
    sellable(stock=None)
    response = post_order(client, order_payload([("creme-test", 1)]))
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "insufficient_stock"
    assert error["items"] == [
        {
            "productId": "creme-test",
            "variantId": error["items"][0]["variantId"],
            "name": "Marque Crème test",
            "requested": 1,
            "available": 0,
            "reason": "stock_unknown",
        }
    ]
    assert not Order.objects.exists() and not StockMovement.objects.exists()


@pytest.mark.django_db
def test_stock_insuffisant_et_rupture(client, sellable):
    sellable(slug="a", stock=2)
    sellable(slug="b", stock=0)
    response = post_order(client, order_payload([("a", 3), ("b", 1)]))
    items = {i["productId"]: i for i in response.json()["error"]["items"]}
    assert response.status_code == 409
    assert (items["a"]["available"], items["a"]["reason"]) == (2, "insufficient")
    assert items["b"]["reason"] == "out_of_stock"
    assert Variant.objects.get(product__slug="a").stock_quantity == 2  # rien n'a bougé


@pytest.mark.django_db
def test_vente_sans_stock_explicitement_autorisee(client, sellable):
    sellable(stock=0, allow_backorder=True)
    assert post_order(client, order_payload([("creme-test", 3)])).status_code == 201
    assert Variant.objects.get().stock_quantity == -3


@pytest.mark.django_db
def test_produits_et_quantites_invalides(client, sellable, product):
    sellable(slug="actif", stock=50)
    product(slug="brouillon")
    assert post_order(client, order_payload([("brouillon", 1)])).status_code == 400
    assert post_order(client, order_payload([("inconnu", 1)])).status_code == 400
    assert post_order(client, order_payload([("actif", 0)])).status_code == 400
    # 15 + 10 du même produit = 25 > 20 autorisés par produit
    assert post_order(client, order_payload([("actif", 15), ("actif", 10)])).status_code == 400
    bad_variant = order_payload([("actif", 1)])
    bad_variant["items"][0]["variantId"] = 999999
    assert post_order(client, bad_variant).status_code == 400
    assert not Order.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("phone", ["0612345678", "+212 6 12 34 56 78", "00212612345678", "06.12.34.56.78"])
def test_telephones_normalises(client, sellable, phone):
    sellable()
    assert post_order(client, order_payload([("creme-test", 1)], phone=phone)).status_code == 201
    assert Customer.objects.get().phone == "+212612345678"


@pytest.mark.django_db
@pytest.mark.parametrize("phone", ["0812345678", "12345", "+33612345678", "06123456789"])
def test_telephones_refuses(client, sellable, phone):
    sellable()
    response = post_order(client, order_payload([("creme-test", 1)], phone=phone))
    assert response.status_code == 400 and "phone" in response.json()["error"]["fields"]["customer"]


@pytest.mark.django_db
def test_villes(client, sellable, shop):
    sellable(stock=50)
    assert post_order(client, order_payload([("creme-test", 1)], city="rabat")).status_code == 201
    assert Order.objects.get().ship_city.name == "Rabat"
    # « Autre ville » acceptée grâce à la zone par défaut, au même tarif
    other = post_order(client, order_payload([("creme-test", 1)], city="Ifrane"))
    assert other.status_code == 201 and other.json()["totals"]["delivery"] == 20
    assert post_order(client, order_payload([("creme-test", 1)], city="<script>")).status_code == 400
    shop.is_default = False
    shop.save()
    assert post_order(client, order_payload([("creme-test", 1)], city="Ifrane")).status_code == 400


@pytest.mark.django_db
def test_livraison_offerte_au_dessus_du_seuil(client, sellable, shop):
    sellable(stock=50)
    shop.free_over_subtotal = Decimal("250")
    shop.save()
    assert post_order(client, order_payload([("creme-test", 1)])).json()["totals"]["delivery"] == 20
    assert post_order(client, order_payload([("creme-test", 2)])).json()["totals"]["delivery"] == 0


# --- Protection contre les abus ------------------------------------------
@pytest.mark.django_db
def test_champ_piege_honeypot(client, sellable):
    sellable()
    response = post_order(client, order_payload([("creme-test", 1)], website="http://spam.example"))
    assert response.status_code == 400
    assert not Order.objects.exists() and AuditLog.objects.filter(action="order.spam_blocked").exists()


@pytest.mark.django_db
@pytest.mark.parametrize("key", ["", "court", "x" * 65, "pas de espaces ici !!"])
def test_cle_d_idempotence_obligatoire(client, sellable, key):
    sellable()
    response = client.post(
        "/api/v1/store/orders", order_payload([("creme-test", 1)]), format="json", HTTP_IDEMPOTENCY_KEY=key
    )
    assert response.status_code == 400 and not Order.objects.exists()


@pytest.mark.django_db
def test_double_envoi_une_seule_commande(client, sellable):
    sellable(stock=10)
    payload = order_payload([("creme-test", 2)])
    first = post_order(client, payload, key="11111111-2222-3333-4444-555555555555")
    second = post_order(client, payload, key="11111111-2222-3333-4444-555555555555")
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["number"] == second.json()["number"]
    assert Order.objects.count() == 1 and Variant.objects.get().stock_quantity == 8
    reused = post_order(client, order_payload([("creme-test", 1)]), key="11111111-2222-3333-4444-555555555555")
    assert reused.status_code == 409 and reused.json()["error"]["code"] == "idempotency_mismatch"


@pytest.mark.django_db
def test_limite_de_commandes_par_telephone(client, sellable):
    from apps.store_settings.models import StoreSettings

    sellable(stock=50)
    StoreSettings.objects.filter(pk=1).update(max_orders_per_phone_per_hour=2)
    for _ in range(2):
        assert post_order(client, order_payload([("creme-test", 1)])).status_code == 201
    blocked = post_order(client, order_payload([("creme-test", 1)], phone="+212612345678"))
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "too_many_orders"
    assert post_order(client, order_payload([("creme-test", 1)], phone="0700000000")).status_code == 201


@pytest.mark.django_db
def test_limitation_de_debit_par_ip(client, sellable):
    from django.core.cache import cache
    from rest_framework.throttling import ScopedRateThrottle

    sellable(stock=50)
    cache.clear()
    with mock.patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"orders": "2/hour", "promo": "2/hour"}):
        codes = [
            post_order(client, order_payload([("creme-test", 1)], phone=f"06000000{i:02d}")).status_code
            for i in range(3)
        ]
    cache.clear()
    assert codes == [201, 201, 429]


# --- Codes promo ----------------------------------------------------------
def coupon(**fields):
    from apps.promotions.models import Coupon

    defaults = {"code": "PROMO", "type": "percentage", "value": Decimal("10")}
    return Coupon.objects.create(**{**defaults, **fields})


@pytest.mark.django_db
@pytest.mark.parametrize(
    "fields,expected",
    [
        ({"type": "percentage", "value": Decimal("10")}, (Decimal("25.80"), 20)),
        ({"type": "fixed_amount", "value": Decimal("50")}, (Decimal("50.00"), 20)),
        ({"type": "fixed_amount", "value": Decimal("999")}, (Decimal("258.00"), 20)),  # jamais négatif
        ({"type": "free_shipping", "value": Decimal("0")}, (Decimal("0"), 0)),
    ],
)
def test_calculs_de_remise(client, sellable, fields, expected):
    sellable(stock=10)
    coupon(**fields)
    data = post_order(client, order_payload([("creme-test", 2)], promo="promo")).json()
    discount, delivery = expected
    assert Decimal(str(data["totals"]["discount"])) == discount and data["totals"]["delivery"] == delivery
    assert Decimal(str(data["totals"]["total"])) == Decimal("258") - discount + delivery
    assert Order.objects.get().coupon_code == "PROMO"


@pytest.mark.django_db
def test_arrondi_au_centime(client, sellable):
    sellable(stock=10, price="149.95")
    coupon(value=Decimal("10"))
    data = post_order(client, order_payload([("creme-test", 1)], promo="PROMO")).json()
    assert data["totals"]["discount"] == 15.0  # 14,995 → 15,00 (arrondi commercial)
    assert data["totals"]["total"] == 154.95


@pytest.mark.django_db
def test_codes_refuses(client, sellable):
    from django.utils import timezone

    sellable(stock=50)
    now = timezone.now()
    coupon(code="INACTIF", is_active=False)
    coupon(code="EXPIRE", ends_at=now - timezone.timedelta(days=1))
    coupon(code="FUTUR", starts_at=now + timezone.timedelta(days=1))
    coupon(code="MINI", min_subtotal=Decimal("500"))
    for code in ("INACTIF", "EXPIRE", "FUTUR", "MINI", "INCONNU"):
        response = post_order(client, order_payload([("creme-test", 1)], promo=code))
        assert response.status_code == 400 and "promoCode" in response.json()["error"]["fields"], code
    assert not Order.objects.exists()


@pytest.mark.django_db
def test_limites_d_utilisation_et_liberation_a_l_annulation(client, sellable, staff):
    sellable(stock=50)
    coupon(code="UNEFOIS", usage_limit=1)
    coupon(code="CLIENT", usage_limit_per_customer=1)
    first = post_order(client, order_payload([("creme-test", 1)], promo="UNEFOIS"))
    assert first.status_code == 201
    second = post_order(client, order_payload([("creme-test", 1)], promo="UNEFOIS", phone="0700000001"))
    assert second.status_code == 400
    assert post_order(client, order_payload([("creme-test", 1)], promo="CLIENT")).status_code == 201
    assert post_order(client, order_payload([("creme-test", 1)], promo="CLIENT")).status_code == 400
    # Annuler la 1re commande libère le code « UNEFOIS »
    order = Order.objects.get(number=first.json()["number"])
    staff().post(f"/api/v1/admin/orders/{order.pk}/status", {"status": "cancelled"}, format="json")
    again = post_order(client, order_payload([("creme-test", 1)], promo="UNEFOIS", phone="0700000002"))
    assert again.status_code == 201


@pytest.mark.django_db
def test_validation_de_code_publique(client, sellable):
    sellable(stock=5)
    coupon(code="MINI", min_subtotal=Decimal("200"))
    url = "/api/v1/store/promo-codes/validate"
    small = client.post(url, {"code": "mini", "items": [{"productId": "creme-test", "qty": 1}]}, format="json")
    assert small.json() == {"valid": False, "message": "Ce code est valable à partir de 200 DH d'achat."}
    ok = client.post(url, {"code": "mini", "items": [{"productId": "creme-test", "qty": 2}]}, format="json").json()
    assert ok == {
        "valid": True,
        "code": "MINI",
        "type": "percentage",
        "value": 10,
        "minSubtotal": 200,
        "discount": 25.8,
    }
    unknown = client.post(url, {"code": "XYZ", "items": [{"productId": "creme-test", "qty": 2}]}, format="json")
    assert unknown.json()["valid"] is False and "MINI" not in unknown.content.decode()
