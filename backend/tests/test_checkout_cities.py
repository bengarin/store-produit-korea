"""Ville du checkout : liste + « Autre » (saisie libre FR/AR), tarifs de livraison inchangés."""

from decimal import Decimal

import pytest

from apps.orders.models import Order
from apps.shipping.models import City, ShippingZone
from apps.store_settings.models import StoreSettings
from tests.conftest import order_payload, post_order


def order(client, city, phone="0612345678"):
    return post_order(client, order_payload([("creme-test", 1)], city=city, phone=phone))


@pytest.mark.django_db
def test_ville_configuree_garde_le_tarif_de_sa_zone(client, sellable, shop):
    sellable(stock=10)
    nord = ShippingZone.objects.create(name="Nord", fee=Decimal("35"))
    City.objects.create(name="Tanger", zone=nord)
    assert order(client, "Tanger").json()["totals"]["delivery"] == 35  # tarif de la zone Nord
    assert order(client, "Casablanca", phone="0611111111").json()["totals"]["delivery"] == 20  # zone Maroc
    assert set(Order.objects.values_list("ship_city_label", flat=True)) == {"Tanger", "Casablanca"}


@pytest.mark.django_db
def test_autre_ville_saisie_en_francais_ou_en_arabe(client, sellable, shop):
    sellable(stock=10)
    for i, city in enumerate(["Sidi Bennour", "زاكورة", "M'diq"]):
        r = order(client, f"  {city}  ", phone=f"061234560{i}")
        assert r.status_code == 201, r.content
        assert r.json()["totals"]["delivery"] == 20  # zone par défaut (« autres villes »), tarif inchangé
    assert list(Order.objects.order_by("id").values_list("ship_city_label", flat=True)) == [
        "Sidi Bennour",
        "زاكورة",
        "M'diq",
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("city", ["", "   ", "x", "<script>", "Rabat 2026", "a" * 81])
def test_ville_vide_ou_invalide_refusee(client, sellable, shop, city):
    sellable(stock=10)
    r = order(client, city)
    assert r.status_code == 400 and "city" in str(r.json())
    assert not Order.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("mode,fee,expected", [("free", None, 0), ("paid", "30", 30)])
def test_sans_aucune_zone_mode_gratuit_ou_montant_unique(client, sellable, mode, fee, expected):
    sellable(stock=10)
    City.objects.all().delete()
    ShippingZone.objects.all().delete()
    s = StoreSettings.load()
    s.delivery_mode, s.delivery_fee = mode, fee
    s.save()
    assert client.get("/api/v1/store/config").json()["allowOtherCity"] is True
    r = order(client, "Tanger")
    assert r.status_code == 201 and r.json()["totals"]["delivery"] == expected
    o = Order.objects.get()
    assert o.ship_city_label == "Tanger" and o.ship_city is None and o.shipping_zone_name == ""
    assert o.shipping_fee == Decimal(expected)


@pytest.mark.django_db
def test_mode_par_zone_sans_zone_par_defaut_reste_refuse(client, sellable, shop):
    sellable(stock=10)
    shop.is_default = False
    shop.save()
    assert client.get("/api/v1/store/config").json()["allowOtherCity"] is False
    assert order(client, "Zagora").status_code == 400  # aucun tarif inventé
    assert order(client, "Rabat", phone="0611111111").status_code == 201  # ville configurée : OK
