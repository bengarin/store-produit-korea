import pytest

from apps.accounts.roles import Role
from apps.audit.models import AuditLog
from apps.catalog.models import Variant
from apps.inventory.models import StockMovement

URL = "/api/v1/admin/inventory"


@pytest.fixture
def unknown_variant(product):
    p = product()
    Variant.objects.filter(product=p).update(stock_quantity=None)
    return Variant.objects.get(product=p)


def adjust(api, variant, mode, quantity, reason="restock", note=""):
    return api.post(
        f"{URL}/adjust",
        {"variantId": variant.pk, "mode": mode, "quantity": quantity, "reason": reason, "note": note},
        format="json",
    )


@pytest.mark.django_db
def test_premier_comptage_puis_mouvements(staff, unknown_variant):
    api = staff(Role.ORDER_MANAGER)
    v = unknown_variant
    refused = adjust(api, v, "delta", 5)
    assert refused.status_code == 400  # on ne peut pas ajouter à un stock inconnu
    first = adjust(api, v, "set", 12, reason="recount", note="Inventaire d'ouverture")
    assert first.status_code == 201
    data = first.json()
    assert (data["reason"], data["quantityBefore"], data["quantityAfter"], data["delta"]) == (
        "initial_count",
        None,
        12,
        12,
    )
    assert adjust(api, v, "delta", 5).json()["quantityAfter"] == 17
    assert adjust(api, v, "delta", -2, reason="damaged").json()["quantityAfter"] == 15
    assert adjust(api, v, "delta", -20, reason="damaged").status_code == 400  # jamais négatif
    assert adjust(api, v, "set", 15, reason="recount").status_code == 400  # rien ne change
    recount = adjust(api, v, "set", 14, reason="initial_count")
    assert recount.json()["reason"] == "recount"  # déjà renseigné : c'est un recomptage
    v.refresh_from_db()
    assert v.stock_quantity == 14 and StockMovement.objects.count() == 4
    assert AuditLog.objects.filter(action="inventory.adjust").count() == 4
    assert adjust(api, v, "delta", 1, reason="order_placed").status_code == 400  # motif réservé aux commandes


@pytest.mark.django_db
def test_historique_en_ajout_seul(staff, unknown_variant):
    adjust(staff(), unknown_variant, "set", 3)
    move = StockMovement.objects.get()
    with pytest.raises(PermissionError):
        move.save()
    with pytest.raises(PermissionError):
        move.delete()
    with pytest.raises(PermissionError):
        StockMovement.objects.update(delta=0)
    with pytest.raises(PermissionError):
        StockMovement.objects.all().delete()


@pytest.mark.django_db
def test_liste_et_etats(staff, product):
    states = {"inconnu": None, "rupture": 0, "bas": 2, "ok": 40}
    for slug, qty in states.items():
        Variant.objects.filter(product=product(slug=slug)).update(stock_quantity=qty)
    api = staff(Role.ANALYST)
    items = {i["productSlug"]: i["state"] for i in api.get(URL).json()["items"]}
    assert items == {"inconnu": "unknown", "rupture": "out_of_stock", "bas": "low", "ok": "ok"}
    for state, slug in (("unknown", "inconnu"), ("out_of_stock", "rupture"), ("low", "bas")):
        assert [i["productSlug"] for i in api.get(f"{URL}?state={state}").json()["items"]] == [slug]


@pytest.mark.django_db
def test_filtres_de_l_historique(staff, unknown_variant, product):
    api = staff()
    adjust(api, unknown_variant, "set", 5)
    other = Variant.objects.get(product=product(slug="autre"))
    adjust(api, other, "delta", 2)
    assert api.get(f"{URL}/movements").json()["total"] == 2
    assert [m["variantId"] for m in api.get(f"{URL}/movements?variant={other.pk}").json()["items"]] == [other.pk]
    assert api.get(f"{URL}/movements?reason=initial_count").json()["total"] == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,can_adjust",
    [
        (Role.OWNER, True),
        (Role.ADMIN, True),
        (Role.ORDER_MANAGER, True),
        (Role.CONTENT_EDITOR, False),
        (Role.ANALYST, False),
        (None, False),
    ],
)
def test_permissions_stock(staff, unknown_variant, role, can_adjust):
    api = staff(role)
    assert api.get(URL).status_code == (200 if role else 403)
    assert adjust(api, unknown_variant, "set", 4).status_code == (201 if can_adjust else 403)


@pytest.mark.django_db
def test_produit_avec_historique_de_stock_non_supprimable(staff, unknown_variant):
    api = staff()
    adjust(api, unknown_variant, "set", 4)
    response = api.delete(f"/api/v1/admin/products/{unknown_variant.product_id}")
    assert response.status_code == 409 and response.json()["error"]["code"] == "product_in_use"
