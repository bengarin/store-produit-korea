"""Statuts, remise en stock, statistiques clients."""

from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.inventory.models import StockMovement
from apps.orders.models import Order
from tests.conftest import order_payload, post_order


@pytest.fixture
def admin_api(staff):
    return staff()


def place(client, qty=2, phone="0612345678"):
    response = post_order(client, order_payload([("creme-test", qty)], phone=phone))
    assert response.status_code == 201, response.content
    return Order.objects.get(number=response.json()["number"])


def set_status(api, order, status, **extra):
    return api.post(f"/api/v1/admin/orders/{order.pk}/status", {"status": status, **extra}, format="json")


def stock():
    from apps.catalog.models import Variant

    return Variant.objects.get().stock_quantity


@pytest.mark.django_db
def test_parcours_complet_puis_retour(client, admin_api, sellable):
    sellable(stock=10)
    order = place(client)
    for status in ("confirmed", "shipped", "delivered"):
        response = set_status(admin_api, order, status)
        assert response.status_code == 200 and response.json()["status"] == status
    order.refresh_from_db()
    customer = Customer.objects.get()
    assert order.payment_status == "paid" and order.delivered_at
    assert customer.total_spent == Decimal("278.00") and stock() == 8

    returned = set_status(admin_api, order, "returned", note="Produit refusé")
    assert returned.json()["paymentStatus"] == "refunded"
    assert stock() == 10  # remis en stock
    customer.refresh_from_db()
    assert customer.total_spent == 0
    history = [(h["fromStatus"], h["toStatus"]) for h in returned.json()["history"]]
    assert history == [
        ("", "pending"),
        ("pending", "confirmed"),
        ("confirmed", "shipped"),
        ("shipped", "delivered"),
        ("delivered", "returned"),
    ]
    assert returned.json()["history"][-1]["changedBy"] == "admin@exemple.ma"
    assert list(StockMovement.objects.order_by("id").values_list("reason", "delta")) == [
        ("order_placed", -2),
        ("order_returned", 2),
    ]


@pytest.mark.django_db
def test_annulation_remet_toujours_en_stock(client, admin_api, sellable):
    sellable(stock=5)
    order = place(client, qty=3)
    assert stock() == 2
    assert set_status(admin_api, order, "cancelled").status_code == 200
    assert stock() == 5
    move = StockMovement.objects.filter(reason="order_cancelled").get()
    assert (move.delta, move.quantity_before, move.quantity_after, move.order) == (3, 2, 5, order)
    assert Customer.objects.get().orders_count == 0  # une commande annulée ne compte pas


@pytest.mark.django_db
def test_retour_sans_remise_en_stock(client, admin_api, sellable):
    sellable(stock=5)
    order = place(client, qty=1)
    for status in ("confirmed", "shipped"):
        set_status(admin_api, order, status)
    set_status(admin_api, order, "returned", restock=False)  # produit abîmé
    assert stock() == 4 and not StockMovement.objects.filter(reason="order_returned").exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path,forbidden",
    [
        ([], "shipped"),
        ([], "delivered"),
        (["cancelled"], "confirmed"),
        (["confirmed", "shipped", "delivered"], "cancelled"),
        (["confirmed", "shipped", "delivered", "returned"], "delivered"),
    ],
)
def test_transitions_interdites(client, admin_api, sellable, path, forbidden):
    sellable(stock=10)
    order = place(client)
    for status in path:
        assert set_status(admin_api, order, status).status_code == 200
    before = stock()
    response = set_status(admin_api, order, forbidden)
    assert response.status_code == 409 and response.json()["error"]["code"] == "invalid_transition"
    assert stock() == before


@pytest.mark.django_db
def test_double_annulation_ne_remet_pas_deux_fois_en_stock(client, admin_api, sellable):
    sellable(stock=5)
    order = place(client, qty=2)
    set_status(admin_api, order, "cancelled")
    assert set_status(admin_api, order, "cancelled").status_code == 409
    assert stock() == 5


@pytest.mark.django_db
def test_statistiques_client_exactes(client, admin_api, sellable):
    sellable(stock=50)
    a = place(client, qty=1, phone="0612345678")
    b = place(client, qty=2, phone="+212 612 345 678")  # même client, autre écriture
    place(client, qty=1, phone="0700000000")
    assert Customer.objects.count() == 2
    customer = Customer.objects.get(phone="+212612345678")
    assert customer.orders_count == 2 and customer.total_spent == 0
    for status in ("confirmed", "shipped", "delivered"):
        set_status(admin_api, a, status)
    set_status(admin_api, b, "cancelled")
    customer.refresh_from_db()
    assert customer.orders_count == 1 and customer.total_spent == Decimal("149.00")  # 129 + 20


@pytest.mark.django_db
def test_produit_commande_jamais_supprimable(client, admin_api, sellable):
    p = sellable(stock=5)
    order = place(client, qty=1)
    set_status(admin_api, order, "cancelled")
    admin_api.post(f"/api/v1/admin/products/{p.pk}/status", {"status": "archived"}, format="json")
    response = admin_api.delete(f"/api/v1/admin/products/{p.pk}")
    assert response.status_code == 409 and response.json()["error"]["code"] == "product_in_use"
    assert Order.objects.filter(pk=order.pk).exists()
