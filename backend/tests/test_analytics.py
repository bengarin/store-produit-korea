"""Les chiffres du tableau de bord sont comparés à des requêtes SQL écrites à la main sur MySQL."""

import datetime as dt
from decimal import Decimal

import pytest
from django.db import connection
from django.utils import timezone

from apps.accounts.roles import Role
from apps.orders.models import Order
from tests.conftest import order_payload, post_order

URL = "/api/v1/admin/analytics/overview"


@pytest.fixture
def mixed_orders(client, staff, sellable):
    """6 commandes : 2 en attente, 1 livrée, 1 annulée, 1 retournée, 1 expédiée."""
    sellable(stock=100)
    api = staff()
    flows = [
        [],
        [],
        ["confirmed", "shipped", "delivered"],
        ["cancelled"],
        ["confirmed", "shipped", "returned"],
        ["confirmed", "shipped"],
    ]
    for i, flow in enumerate(flows):
        number = post_order(client, order_payload([("creme-test", i + 1)], phone=f"06111111{i:02d}")).json()["number"]
        order = Order.objects.get(number=number)
        for status in flow:
            assert (
                api.post(f"/api/v1/admin/orders/{order.pk}/status", {"status": status}, format="json").status_code
                == 200
            )
    return api


def sql(query, params):
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()


@pytest.mark.django_db
def test_indicateurs_egaux_aux_requetes_sql(mixed_orders):
    today = timezone.localdate()
    data = mixed_orders.get(URL).json()
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(dt.datetime.combine(today - dt.timedelta(days=29), dt.time.min), tz)
    end = timezone.make_aware(dt.datetime.combine(today + dt.timedelta(days=1), dt.time.min), tz)
    window = "FROM orders_order WHERE placed_at >= %s AND placed_at < %s"

    count, gross, valid, revenue = sql(
        "SELECT COUNT(*),"
        " SUM(CASE WHEN status NOT IN ('cancelled','returned') THEN total ELSE 0 END),"
        " SUM(CASE WHEN status NOT IN ('cancelled','returned') THEN 1 ELSE 0 END),"
        " SUM(CASE WHEN status = 'delivered' THEN total ELSE 0 END) " + window,
        [start, end],
    )
    k = data["kpis"]
    assert k["orders"] == count == 6
    assert Decimal(str(k["grossSales"])) == gross
    assert Decimal(str(k["revenue"])) == revenue
    assert Decimal(str(k["averageOrderValue"])) == (gross / valid).quantize(Decimal("0.01"))
    for status in ("pending", "delivered", "cancelled", "returned", "shipped", "confirmed"):
        (n,) = sql("SELECT COUNT(*) " + window + " AND status = %s", [start, end, status])
        assert k[status] == n, status
    assert (k["pending"], k["delivered"], k["cancelled"], k["returned"], k["shipped"]) == (2, 1, 1, 1, 1)
    # Prix 129 DH + 20 DH de livraison : livrée = 3 articles → 407 DH
    assert k["revenue"] == 407
    assert data["toProcess"] == 2
    assert sum(d["orders"] for d in data["series"]) == 6 and len(data["series"]) == 30
    assert data["series"][-1]["date"] == today.isoformat()
    assert Decimal(str(sum(d["grossSales"] for d in data["series"]))) == gross
    assert [o["number"] for o in data["recentOrders"]] == list(
        Order.objects.order_by("-placed_at", "-id").values_list("number", flat=True)[:8]
    )


@pytest.mark.django_db
def test_periode_vide_et_validation(mixed_orders):
    empty = mixed_orders.get(f"{URL}?from=2020-01-01&to=2020-01-31").json()
    assert empty["kpis"]["orders"] == 0 and empty["kpis"]["averageOrderValue"] == 0 and len(empty["series"]) == 31
    assert mixed_orders.get(f"{URL}?from=2026-02-10&to=2026-02-01").status_code == 400
    assert mixed_orders.get(f"{URL}?from=2020-01-01&to=2026-01-01").status_code == 400  # > 366 jours
    assert mixed_orders.get(f"{URL}?from=hier").status_code == 400


@pytest.mark.django_db
def test_alertes_de_stock(staff, product):
    from apps.catalog.models import Variant

    for slug, qty in {"inconnu": None, "rupture": 0, "bas": 2, "ok": 50}.items():
        Variant.objects.filter(product=product(slug=slug)).update(stock_quantity=qty)
    data = staff().get(URL).json()
    assert data["stock"] == {"unknown": 1, "outOfStock": 1, "low": 1}
    assert [a["productName"] for a in data["stockAlerts"]] == ["Marque Crème test"] * 3
    assert [a["stockQuantity"] for a in data["stockAlerts"]] == [None, 0, 2]


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
def test_acces_tableau_de_bord(staff, role, code):
    assert staff(role).get(URL).status_code == code


@pytest.mark.django_db
def test_correction_manuelle_exige_une_note(staff, product):
    from apps.catalog.models import Variant

    v = Variant.objects.get(product=product())
    url = "/api/v1/admin/inventory/adjust"
    base = {"variantId": v.pk, "mode": "delta", "quantity": -1, "reason": "manual_adjustment"}
    response = staff().post(url, base, format="json")
    assert response.status_code == 400 and "note" in response.json()["error"]["fields"]
    assert staff(Role.OWNER).post(url, {**base, "note": "Erreur de saisie"}, format="json").status_code == 201


@pytest.mark.django_db
def test_inventaire_renvoie_l_image_du_produit(staff, product):
    product()
    item = staff().get("/api/v1/admin/inventory").json()["items"][0]
    assert item["productImage"].endswith(".webp")
