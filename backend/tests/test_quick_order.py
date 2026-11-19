"""Commande rapide : réglage boutique + produit, action groupée, commande normale via le même processus."""

import pytest

from apps.accounts.roles import Role
from apps.catalog.models import Product
from apps.orders.models import Order
from apps.store_settings.models import StoreSettings
from tests.conftest import order_payload, post_order

ADMIN = "/api/v1/admin"
STORE = "/api/v1/store"


def enable_shop(on=True):
    s = StoreSettings.load()
    s.quick_order_enabled = on
    s.save()


def quick(items, **extra):
    return order_payload(items, source="quick", **extra)


@pytest.mark.django_db
def test_par_defaut_desactivee_et_heritage(client, sellable, shop):
    p = sellable()
    assert p.quick_order == "inherit"
    assert client.get(f"{STORE}/config").json()["quickOrderEnabled"] is False
    assert client.get(f"{STORE}/products/{p.slug}").json()["quickOrder"] == "inherit"
    # Boutique désactivée + produit « hériter » : refusée, aucune commande.
    r = post_order(client, quick([(p.slug, 1)]))
    assert r.status_code == 400 and Order.objects.count() == 0


@pytest.mark.django_db
def test_commande_rapide_cree_une_commande_normale(client, sellable, shop):
    enable_shop()
    p = sellable(stock=5)
    r = post_order(client, quick([(p.slug, 2)]))
    assert r.status_code == 201, r.content
    order = Order.objects.get()
    assert order.item_count == 2 and order.status == Order.Status.PENDING
    assert "Commande rapide" in order.internal_note
    assert order.history.first().note.startswith("Commande rapide")
    p.variants.get().refresh_from_db()
    assert p.variants.get().stock_quantity == 3  # même règle de stock que le panier


@pytest.mark.django_db
def test_stock_insuffisant_aucune_commande(client, sellable, shop):
    enable_shop()
    p = sellable(stock=1)
    r = post_order(client, quick([(p.slug, 3)]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "insufficient_stock"
    assert Order.objects.count() == 0
    assert p.variants.get().stock_quantity == 1


@pytest.mark.django_db
def test_choix_du_produit_prioritaire(client, sellable, shop):
    a, b = sellable(slug="a"), sellable(slug="b")
    Product.objects.filter(pk=a.pk).update(quick_order="on")  # boutique désactivée, produit activé
    assert post_order(client, quick([("a", 1)])).status_code == 201
    enable_shop()
    Product.objects.filter(pk=b.pk).update(quick_order="off")  # boutique activée, produit désactivé
    assert post_order(client, quick([("b", 1)])).status_code == 400
    # Un seul produit par commande rapide.
    assert post_order(client, quick([("a", 1), ("b", 1)])).status_code == 400
    # Le panier n'est jamais concerné par ce réglage.
    assert post_order(client, order_payload([("b", 1)])).status_code == 201


@pytest.mark.django_db
def test_produit_inactif_refuse(client, product, shop):
    enable_shop()
    product(slug="brouillon", status="draft", quick_order="on")
    assert post_order(client, quick([("brouillon", 1)])).status_code == 400
    assert Order.objects.count() == 0


@pytest.mark.django_db
def test_reglages_admin(staff, sellable):
    api = staff(Role.ADMIN)
    assert api.get(f"{ADMIN}/settings").json()["quickOrderEnabled"] is False
    assert api.patch(f"{ADMIN}/settings", {"quickOrderEnabled": True}, format="json").status_code == 200
    assert StoreSettings.load().quick_order_enabled is True
    p = sellable()
    r = api.patch(f"{ADMIN}/products/{p.pk}", {"quickOrder": "off"}, format="json")
    assert r.status_code == 200 and r.json()["quickOrder"] == "off"
    assert api.patch(f"{ADMIN}/products/{p.pk}", {"quickOrder": "peut-être"}, format="json").status_code == 400


@pytest.mark.django_db
def test_action_groupee(staff, sellable):
    api = staff(Role.CONTENT_EDITOR)
    a, b, c = sellable(slug="a", price="10.00"), sellable(slug="b"), sellable(slug="c")
    before = {p.pk: (p.status, p.updated_at) for p in Product.objects.all()}
    r = api.post(f"{ADMIN}/products/quick-order", {"productIds": [a.pk, b.pk], "quickOrder": "on"}, format="json")
    assert r.status_code == 200 and r.json()["updated"] == 2
    modes = dict(Product.objects.values_list("slug", "quick_order"))
    assert modes == {"a": "on", "b": "on", "c": "inherit"}
    # Rien d'autre ne change (statut, prix).
    assert all(p.status == before[p.pk][0] for p in Product.objects.all())
    assert str(Product.objects.get(slug="a").variants.get().price) == "10.00"
    # Identifiant inconnu : refus, rien n'est modifié.
    r = api.post(f"{ADMIN}/products/quick-order", {"productIds": [c.pk, 99999], "quickOrder": "off"}, format="json")
    assert r.status_code == 400 and Product.objects.get(pk=c.pk).quick_order == "inherit"
    # Rôle sans droit catalogue : refusé.
    viewer = staff(Role.ANALYST)
    r = viewer.post(f"{ADMIN}/products/quick-order", {"productIds": [c.pk], "quickOrder": "off"}, format="json")
    assert r.status_code == 403
