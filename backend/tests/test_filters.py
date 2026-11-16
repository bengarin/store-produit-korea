"""Filtres de la page produits : groupes / valeurs gérés dans l'admin, valeurs des produits, API publique, droits."""

import pytest

from apps.accounts.roles import Role
from apps.audit.models import AuditLog
from apps.catalog.models import FilterGroup, FilterOption, Product, Variant

STORE = "/api/v1/store"
ADMIN = "/api/v1/admin"


def make_groups(api):
    sol = api.post(f"{ADMIN}/filters", {"name": "Mes solutions", "nameAr": "حلولي"}, format="json").json()
    zone = api.post(f"{ADMIN}/filters", {"name": "Zone d'application"}, format="json").json()
    hyd = api.post(
        f"{ADMIN}/filters/{sol['id']}/options", {"name": "Hydratation", "nameAr": "ترطيب"}, format="json"
    ).json()
    acne = api.post(f"{ADMIN}/filters/{sol['id']}/options", {"name": "Imperfections"}, format="json").json()
    yeux = api.post(f"{ADMIN}/filters/{zone['id']}/options", {"name": "Yeux"}, format="json").json()
    return sol, zone, hyd, acne, yeux


@pytest.mark.django_db
def test_groupes_valeurs_et_api_publique(client, staff):
    api = staff(Role.ADMIN)
    sol, zone, hyd, acne, yeux = make_groups(api)
    assert sol["slug"] == "mes-solutions" and hyd["slug"] == "hydratation"
    items = client.get(f"{STORE}/filters").json()["items"]
    assert items == [
        {
            "id": "mes-solutions", "label": "Mes solutions", "translations": {"ar": {"label": "حلولي"}},
            "options": [
                {"id": "hydratation", "label": "Hydratation", "translations": {"ar": {"label": "ترطيب"}}},
                {"id": "imperfections", "label": "Imperfections"},
            ],
        },
        {"id": "zone-dapplication", "label": "Zone d'application", "options": [{"id": "yeux", "label": "Yeux"}]},
    ]  # fmt: skip
    # Réordonner les groupes et les valeurs.
    assert api.post(f"{ADMIN}/filters/reorder", {"ids": [zone["id"], sol["id"]]}, format="json").status_code == 204
    assert (
        api.post(
            f"{ADMIN}/filters/{sol['id']}/options/reorder", {"ids": [acne["id"], hyd["id"]]}, format="json"
        ).status_code
        == 204
    )
    items = client.get(f"{STORE}/filters").json()["items"]
    assert [g["id"] for g in items] == ["zone-dapplication", "mes-solutions"]
    assert [o["id"] for o in items[1]["options"]] == ["imperfections", "hydratation"]
    # Liste incomplète refusée.
    assert api.post(f"{ADMIN}/filters/reorder", {"ids": [zone["id"]]}, format="json").status_code == 400
    # Masquer une valeur puis un groupe ; un groupe sans valeur visible disparaît.
    api.patch(f"{ADMIN}/filter-options/{yeux['id']}", {"isActive": False}, format="json")
    assert [g["id"] for g in client.get(f"{STORE}/filters").json()["items"]] == ["mes-solutions"]
    api.patch(f"{ADMIN}/filters/{sol['id']}", {"isActive": False, "name": "Solutions"}, format="json")
    assert client.get(f"{STORE}/filters").json()["items"] == []
    assert FilterGroup.objects.get(pk=sol["id"]).name == "Solutions"


@pytest.mark.django_db
def test_valeurs_du_produit_sans_toucher_au_reste(client, staff, sellable):
    api = staff(Role.CONTENT_EDITOR)
    _sol, _zone, hyd, _acne, yeux = make_groups(staff(Role.OWNER))
    adm = staff(Role.ADMIN)
    product = sellable()
    before = list(Variant.objects.values_list("pk", "price", "stock_quantity"))
    status, cats = product.status, list(product.category_links.values_list("category_id", flat=True))
    r = api.put(f"{ADMIN}/products/{product.pk}/filters", {"optionIds": [hyd["id"], yeux["id"]]}, format="json")
    assert r.status_code == 200 and r.json() == {"optionIds": sorted([hyd["id"], yeux["id"]])}
    assert api.get(f"{ADMIN}/products/{product.pk}/filters").json()["optionIds"] == sorted([hyd["id"], yeux["id"]])
    payload = client.get(f"{STORE}/products/{product.slug}").json()
    assert sorted(payload["filters"]) == ["mes-solutions:hydratation", "zone-dapplication:yeux"]
    assert "publishedAt" in payload
    # Rien d'autre ne change.
    assert list(Variant.objects.values_list("pk", "price", "stock_quantity")) == before
    product.refresh_from_db()
    assert product.status == status and list(product.category_links.values_list("category_id", flat=True)) == cats
    # Valeur masquée : absente de la boutique, conservée dans l'admin.
    adm.patch(f"{ADMIN}/filter-options/{yeux['id']}", {"isActive": False}, format="json")
    assert client.get(f"{STORE}/products/{product.slug}").json()["filters"] == ["mes-solutions:hydratation"]
    # Supprimer une valeur : retirée du produit, produit intact.
    assert adm.delete(f"{ADMIN}/filter-options/{hyd['id']}").status_code == 204
    assert Product.objects.filter(pk=product.pk).exists()
    assert list(product.filter_options.values_list("pk", flat=True)) == [yeux["id"]]
    # Valeur inconnue refusée.
    assert api.put(f"{ADMIN}/products/{product.pk}/filters", {"optionIds": [999999]}, format="json").status_code == 400
    assert AuditLog.objects.filter(action="product.filters").exists()


@pytest.mark.django_db
def test_supprimer_un_groupe_supprime_ses_valeurs(staff, sellable):
    api = staff(Role.ADMIN)
    sol, _zone, hyd, _acne, _yeux = make_groups(api)
    product = sellable()
    api.put(f"{ADMIN}/products/{product.pk}/filters", {"optionIds": [hyd["id"]]}, format="json")
    assert api.delete(f"{ADMIN}/filters/{sol['id']}").status_code == 204
    assert not FilterOption.objects.filter(group_id=sol["id"]).exists()
    assert Product.objects.filter(pk=product.pk).exists() and not product.filter_options.exists()


@pytest.mark.django_db
def test_droits(client, staff, sellable):
    owner = staff(Role.OWNER)
    _sol, *_ = make_groups(owner)
    product = sellable()
    apis = {role: staff(role) for role in (Role.CONTENT_EDITOR, Role.ORDER_MANAGER, Role.ANALYST)}
    for api in apis.values():
        assert api.post(f"{ADMIN}/filters", {"name": "X"}, format="json").status_code == 403
        assert api.get(f"{ADMIN}/filters").status_code == 200
    for role in (Role.ORDER_MANAGER, Role.ANALYST):
        r = apis[role].put(f"{ADMIN}/products/{product.pk}/filters", {"optionIds": []}, format="json")
        assert r.status_code == 403
    assert client.post(f"{ADMIN}/filters", {"name": "X"}, content_type="application/json").status_code in (401, 403)
    assert staff(Role.ADMIN).post(f"{ADMIN}/filters", {"name": "<b>"}, format="json").status_code == 400
