"""Menu « Catégories » : sous-catégories, masquage, ordre, rattachement des produits, droits, exemples."""

from io import StringIO

import pytest
from django.core.management import call_command

from apps.accounts.roles import Role
from apps.catalog.models import Category, Product, ProductCategory, Variant

STORE = "/api/v1/store"
ADMIN = "/api/v1/admin"


def menu(client):
    return client.get(f"{STORE}/categories").json()["items"]


@pytest.mark.django_db
def test_sous_categories_dans_le_menu_et_dans_l_ordre(client, staff):
    api = staff(Role.ADMIN)
    hyd = Category.objects.get(slug="hydratation")
    a = api.post(
        f"{ADMIN}/categories", {"name": "Gels apaisants", "nameAr": "جل مهدّئ", "parentId": hyd.pk}, format="json"
    )
    b = api.post(f"{ADMIN}/categories", {"name": "Crèmes hydratantes", "parentId": hyd.pk}, format="json")
    assert a.status_code == b.status_code == 201
    items = menu(client)
    ids = [i["id"] for i in items]
    # Chaque catégorie principale est suivie de ses sous-catégories.
    assert ids.index("hydratation") < ids.index(a.json()["slug"]) < ids.index(b.json()["slug"])
    sub = next(i for i in items if i["id"] == a.json()["slug"])
    assert sub == {
        "id": a.json()["slug"],
        "label": "Gels apaisants",
        "parent": "hydratation",
        "translations": {"ar": {"label": "جل مهدّئ"}},
    }
    # Renommer depuis l'admin : visible dans le menu au prochain chargement.
    api.patch(f"{ADMIN}/categories/{b.json()['id']}", {"name": "Crèmes riches"}, format="json")
    assert "Crèmes riches" in [i["label"] for i in menu(client)]
    # Réordonner : les sous-catégories suivent la nouvelle position.
    order = list(Category.objects.order_by("position", "id").values_list("pk", flat=True))
    order.remove(b.json()["id"])
    order.insert(0, b.json()["id"])
    assert api.post(f"{ADMIN}/categories/reorder", {"ids": order}, format="json").status_code == 204
    ids = [i["id"] for i in menu(client)]
    assert ids.index(b.json()["slug"]) < ids.index(a.json()["slug"])


@pytest.mark.django_db
def test_categorie_masquee_masque_ses_sous_categories_mais_garde_les_produits(client, staff, product):
    api = staff(Role.ADMIN)
    eclat = Category.objects.get(slug="eclat")
    sub = Category.objects.create(slug="soins-du-teint", name="Soins du teint", parent=eclat)
    p = product(slug="creme-eclat", status="active")
    ProductCategory.objects.create(product=p, category=sub, position=5)
    assert "creme-eclat" in [x["id"] for x in client.get(f"{STORE}/products").json()["items"]]
    assert "soins-du-teint" in client.get(f"{STORE}/products/creme-eclat").json()["categories"]

    assert api.patch(f"{ADMIN}/categories/{eclat.pk}", {"isActive": False}, format="json").status_code == 200
    ids = [i["id"] for i in menu(client)]
    assert "eclat" not in ids and "soins-du-teint" not in ids
    assert "soins-du-teint" not in client.get(f"{STORE}/products/creme-eclat").json()["categories"]
    # Le produit et ses liens restent dans l'administration.
    assert ProductCategory.objects.filter(product=p, category=sub).exists()
    assert api.get(f"{ADMIN}/products/{p.pk}").status_code == 200
    assert client.get(f"{STORE}/products/creme-eclat").status_code == 200


@pytest.mark.django_db
def test_menu_a_deux_niveaux_et_suppression_protegee(staff):
    api = staff(Role.ADMIN)
    hyd = Category.objects.get(slug="hydratation")
    sub = api.post(f"{ADMIN}/categories", {"name": "Gels", "parentId": hyd.pk}, format="json").json()
    third = api.post(f"{ADMIN}/categories", {"name": "Trop profond", "parentId": sub["id"]}, format="json")
    assert third.status_code == 400
    # Une catégorie qui a des sous-catégories ne devient pas sous-catégorie, et ne se supprime pas.
    other = Category.objects.get(slug="eclat")
    assert api.patch(f"{ADMIN}/categories/{hyd.pk}", {"parentId": other.pk}, format="json").status_code == 400
    response = api.delete(f"{ADMIN}/categories/{hyd.pk}")
    assert response.status_code == 409 and response.json()["error"]["code"] == "category_has_children"


@pytest.mark.django_db
def test_rattacher_des_produits_a_une_sous_categorie(staff, product):
    api = staff(Role.ADMIN)
    hyd = Category.objects.get(slug="hydratation")
    sub = Category.objects.create(slug="gels-apaisants", name="Gels apaisants", parent=hyd)
    p1, p2 = product(slug="gel-1"), product(slug="gel-2", status="active")
    before = list(Variant.objects.order_by("pk").values("price", "stock_quantity"))
    url = f"{ADMIN}/categories/{sub.pk}/products"
    assert api.put(url, {"productIds": [p1.pk, p2.pk]}, format="json").status_code == 200
    assert sorted(api.get(url).json()["productIds"]) == [p1.pk, p2.pk]
    # Les autres catégories des produits sont conservées ; la nouvelle est ajoutée à la fin.
    assert list(p1.category_links.order_by("position").values_list("category__slug", flat=True)) == [
        "cat-gel-1",
        "gels-apaisants",
    ]
    # Retrait : seul le lien de cette catégorie disparaît.
    assert api.put(url, {"productIds": [p2.pk]}, format="json").status_code == 200
    assert not ProductCategory.objects.filter(product=p1, category=sub).exists()
    assert ProductCategory.objects.filter(product=p1, category__slug="cat-gel-1").exists()
    assert list(Variant.objects.order_by("pk").values("price", "stock_quantity")) == before
    assert set(Product.objects.values_list("status", flat=True)) == {"draft", "active"}
    # Un produit en ligne garde au moins une catégorie.
    ProductCategory.objects.filter(product=p2).exclude(category=sub).delete()
    response = api.put(url, {"productIds": []}, format="json")
    assert response.status_code == 409 and response.json()["error"]["code"] == "product_needs_category"
    assert api.put(url, {"productIds": [999999]}, format="json").status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.CONTENT_EDITOR, Role.ORDER_MANAGER, Role.ANALYST])
def test_gestion_reservee_aux_administrateurs(staff, role):
    api = staff(role)
    hyd = Category.objects.get(slug="hydratation")
    assert api.get(f"{ADMIN}/categories").status_code == 200  # lecture (formulaire produit)
    assert api.post(f"{ADMIN}/categories", {"name": "X", "parentId": hyd.pk}, format="json").status_code == 403
    assert api.patch(f"{ADMIN}/categories/{hyd.pk}", {"isActive": False}, format="json").status_code == 403
    assert api.put(f"{ADMIN}/categories/{hyd.pk}/products", {"productIds": []}, format="json").status_code == 403


@pytest.mark.django_db
def test_exemples_du_menu_idempotents(client):
    out = StringIO()
    call_command("seed_menu_categories", "--dry-run", stdout=out)
    assert "APERÇU" in out.getvalue() and not Category.objects.filter(slug="gels-apaisants").exists()
    call_command("seed_menu_categories", stdout=StringIO())
    Category.objects.filter(slug="patchs-yeux").update(name="Patchs (renommé)")
    call_command("seed_menu_categories", stdout=StringIO())
    subs = Category.objects.filter(parent__isnull=False)
    assert subs.count() == 6 and subs.get(slug="patchs-yeux").name == "Patchs (renommé)"
    assert not ProductCategory.objects.filter(category__in=subs).exists()  # aucun produit rattaché d'office
    labels = {i["id"]: i.get("parent") for i in menu(client)}
    assert labels["gels-apaisants"] == "hydratation" and labels["contour-des-yeux"] == "anti-age"
