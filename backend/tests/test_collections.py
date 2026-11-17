"""
Collections « Soins naturels » / « Beauté chinoise » : un produit = une fiche, un stock, dans 0, 1 ou 2 collections.
Règles vérifiées par le serveur : pays de fabrication exigé (Chine) et liste d'ingrédients exigée (naturels).
"""

import importlib

import pytest
from rest_framework.test import APIClient

from apps.accounts.roles import Role
from apps.audit.models import AuditLog
from apps.catalog.models import Collection, Product, Variant

STORE = "/api/v1/store"
ADMIN = "/api/v1/admin"


def seeded():
    """Les 2 collections de la migration 0009 (recréées si un test « transactionnel » a vidé la base ; idempotent)."""
    from django.apps import apps as django_apps

    importlib.import_module("apps.catalog.migrations.0009_seed_collections").create_collections(django_apps, None)
    return Collection.objects.get(slug="soins-naturels"), Collection.objects.get(slug="beaute-chinoise")


def _live(chinoise):
    """Produit en ligne, fabriqué en Chine, avec ingrédients : éligible aux deux collections."""
    p = Product.objects.create(
        slug="vitrine", brand="M", name="Vitrine", status="active", origin_country="CN", ingredients=["Eau"]
    )
    chinoise.products.add(p)
    return p


def put_products(api, collection, ids):
    return api.put(f"{ADMIN}/collections/{collection.pk}/products", {"productIds": ids}, format="json")


@pytest.mark.django_db
def test_collections_creees_par_migrate_sans_produit(client):
    naturels, chinoise = seeded()
    assert (naturels.name, naturels.name_ar, naturels.require_ingredients, naturels.required_origin) == (
        "Soins naturels", "عناية طبيعية", True, ""
    )  # fmt: skip
    assert (chinoise.name, chinoise.name_ar, chinoise.required_origin) == ("Beauté chinoise", "الجمال الصيني", "CN")
    assert naturels.products.count() == chinoise.products.count() == 0
    # Collection vide : rien dans la boutique (ni menu, ni accueil, ni page).
    assert client.get(f"{STORE}/collections").json()["items"] == []
    assert client.get("/collections/soins-naturels").status_code == 404


@pytest.mark.django_db
def test_regles_origine_et_ingredients(staff, product):
    api = staff(Role.ADMIN)
    naturels, chinoise = seeded()
    p = product(slug="gel", status="active")
    # Origine non renseignée : refusé dans « Beauté chinoise », avec la raison.
    r = put_products(api, chinoise, [p.pk])
    assert r.status_code == 400 and "Chine" in r.json()["error"]["fields"]["productIds"][0]
    # Sans liste d'ingrédients : refusé dans « Soins naturels ».
    r = put_products(api, naturels, [p.pk])
    assert r.status_code == 400 and "ingrédients" in r.json()["error"]["fields"]["productIds"][0]
    # L'éligibilité est visible avant d'enregistrer.
    rows = api.get(f"{ADMIN}/collections/{chinoise.pk}/products").json()["products"]
    row = next(x for x in rows if x["id"] == p.pk)
    assert row["eligible"] is False and row["reasons"] and row["originCountry"] == ""
    # Informations vérifiées saisies sur la fiche : accepté dans les deux collections.
    assert (
        api.patch(
            f"{ADMIN}/products/{p.pk}", {"originCountry": "CN", "ingredients": ["Aloe vera"]}, format="json"
        ).status_code
        == 200
    )
    assert put_products(api, chinoise, [p.pk]).status_code == 200
    assert put_products(api, naturels, [p.pk]).status_code == 200
    assert set(p.collections.values_list("slug", flat=True)) == {"soins-naturels", "beaute-chinoise"}


@pytest.mark.django_db
def test_un_produit_dans_deux_collections_une_seule_fiche(client, staff, product):
    api = staff(Role.ADMIN)
    naturels, chinoise = seeded()
    p = product(slug="gel", status="active", origin_country="CN", ingredients=["Aloe vera"])
    variants_before = list(Variant.objects.filter(product=p).values("pk", "price", "stock_quantity"))
    r = api.patch(f"{ADMIN}/products/{p.pk}", {"collectionIds": [naturels.pk, chinoise.pk]}, format="json")
    assert r.status_code == 200
    assert [c["slug"] for c in r.json()["collections"]] == ["soins-naturels", "beaute-chinoise"]
    # Aucune copie : un seul produit, mêmes variantes, même prix, même stock.
    assert Product.objects.filter(slug="gel").count() == 1
    assert list(Variant.objects.filter(product=p).values("pk", "price", "stock_quantity")) == variants_before
    data = client.get(f"{STORE}/products/gel").json()
    assert data["collections"] == ["soins-naturels", "beaute-chinoise"] and data["origin"] == "CN"
    items = client.get(f"{STORE}/collections").json()["items"]
    assert [c["id"] for c in items] == ["soins-naturels", "beaute-chinoise"]
    assert items[1]["translations"]["ar"]["label"] == "الجمال الصيني"
    assert items[0]["productCount"] == 1 and items[0]["image"]["src"]  # image de secours : photo du produit
    # Filtre de la liste admin.
    assert [x["slug"] for x in api.get(f"{ADMIN}/products?collection=beaute-chinoise").json()["items"]] == ["gel"]


@pytest.mark.django_db
def test_changer_origine_ou_ingredients_ensuite_est_refuse(staff, product):
    api = staff(Role.ADMIN)
    naturels, chinoise = seeded()
    p = product(slug="gel", status="active", origin_country="CN", ingredients=["Aloe vera"])
    naturels.products.add(p)
    chinoise.products.add(p)
    r = api.patch(f"{ADMIN}/products/{p.pk}", {"originCountry": "KR"}, format="json")
    assert r.status_code == 400 and "Chine" in str(r.json())
    r = api.patch(f"{ADMIN}/products/{p.pk}", {"ingredients": []}, format="json")
    assert r.status_code == 400 and "ingrédients" in str(r.json())
    p.refresh_from_db()
    assert p.origin_country == "CN" and p.ingredients == ["Aloe vera"]
    # Durcir la règle d'une collection déjà remplie : refusé tant que des produits ne la respectent pas.
    naturels.products.remove(p)
    p2 = product(slug="creme", status="active", ingredients=["Eau"], origin_country="KR")
    naturels.products.add(p2)
    r = api.patch(f"{ADMIN}/collections/{naturels.pk}", {"requiredOrigin": "CN"}, format="json")
    assert r.status_code == 400
    assert Collection.objects.get(pk=naturels.pk).required_origin == ""


@pytest.mark.django_db
def test_visibilite_publique(client, staff, product):
    api = staff(Role.ADMIN)
    naturels, _ = seeded()
    draft = product(slug="brouillon", status="draft", ingredients=["Eau"])
    naturels.products.add(draft)
    assert client.get(f"{STORE}/collections").json()["items"] == []  # aucun produit EN LIGNE
    live = product(slug="gel", status="active", ingredients=["Aloe vera"])
    naturels.products.add(live)
    assert [c["productCount"] for c in client.get(f"{STORE}/collections").json()["items"]] == [1]
    api.patch(f"{ADMIN}/collections/{naturels.pk}", {"isActive": False}, format="json")
    assert client.get(f"{STORE}/collections").json()["items"] == []
    assert client.get(f"{STORE}/products/gel").json()["collections"] == []
    # Pas d'origine renseignée = pas de champ « origin » (rien n'est supposé).
    assert "origin" not in client.get(f"{STORE}/products/gel").json()


@pytest.mark.django_db
def test_admin_textes_image_ordre_et_audit(staff, media):
    api = staff(Role.ADMIN)
    naturels, chinoise = seeded()
    img = media()
    r = api.patch(
        f"{ADMIN}/collections/{naturels.pk}",
        {"description": "Nouveau texte", "descriptionAr": "نص جديد", "imageId": img.pk, "imageAlt": "Soins"},
        format="json",
    )
    assert r.status_code == 200 and r.json()["image"]["id"] == img.pk
    assert api.patch(f"{ADMIN}/collections/{naturels.pk}", {"name": "<b>x</b>"}, format="json").status_code == 400
    assert (
        api.post(f"{ADMIN}/collections/reorder", {"ids": [chinoise.pk, naturels.pk]}, format="json").status_code == 204
    )
    assert [c["slug"] for c in api.get(f"{ADMIN}/collections").json()] == ["beaute-chinoise", "soins-naturels"]
    Collection.objects.get(pk=naturels.pk).products.add(_live(chinoise))
    assert [c["id"] for c in APIClient().get(f"{STORE}/collections").json()["items"]] == [
        "beaute-chinoise", "soins-naturels"
    ]  # fmt: skip
    created = api.post(f"{ADMIN}/collections", {"name": "Coffrets"}, format="json").json()
    assert created["slug"] == "coffrets"
    assert api.delete(f"{ADMIN}/collections/{created['id']}").status_code == 204
    actions = set(AuditLog.objects.values_list("action", flat=True))
    assert {"collection.update", "collection.reorder", "collection.create", "collection.delete"} <= actions


@pytest.mark.django_db
def test_droits(staff, product):
    naturels, _ = seeded()
    p = product(slug="gel", status="active", ingredients=["Aloe vera"])
    editor = staff(Role.CONTENT_EDITOR)
    # L'éditeur range les produits, mais ne modifie pas les collections elles-mêmes.
    assert put_products(editor, naturels, [p.pk]).status_code == 200
    assert editor.patch(f"{ADMIN}/collections/{naturels.pk}", {"name": "X"}, format="json").status_code == 403
    assert editor.post(f"{ADMIN}/collections", {"name": "X"}, format="json").status_code == 403
    analyst = staff(Role.ANALYST)
    assert analyst.get(f"{ADMIN}/collections").status_code == 200
    assert put_products(analyst, naturels, []).status_code == 403


@pytest.mark.django_db
def test_pages_serveur_fr_ar_et_sitemap(client, product):
    naturels, chinoise = seeded()
    p = product(slug="gel", status="active", origin_country="CN", ingredients=["Aloe vera"])
    naturels.products.add(p)
    chinoise.products.add(p)
    html = client.get("/collections/beaute-chinoise").content.decode()
    assert "<title>Beauté chinoise — " in html and "/produits/gel" in html
    assert 'hreflang="ar-MA" href="http://testserver/ar/collections/beaute-chinoise"' in html
    html_ar = client.get("/ar/collections/beaute-chinoise").content.decode()
    assert "الجمال الصيني" in html_ar and 'dir="rtl"' in html_ar
    assert client.get("/collections/inconnue").status_code == 404
    home = client.get("/").content.decode()
    assert "/collections/soins-naturels" in home and "Découvrir la collection" in home
    product_html = client.get("/produits/gel").content.decode()
    assert "Pays de fabrication : Chine" in product_html
    assert "بلد الصنع : الصين" in client.get("/ar/produits/gel").content.decode()
    sitemap = client.get("/sitemap.xml").content.decode()
    assert "/collections/soins-naturels</loc>" in sitemap and "/ar/collections/beaute-chinoise</loc>" in sitemap
