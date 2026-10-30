"""
API publique : comparée au CONTRAT du front (catalogue local exporté dans demo_catalog.json,
lu par src/services/productService.js → normalizeProduct).
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.catalog.models import Category, Product, Variant

FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "apps/catalog/fixtures/demo_catalog.json").read_text(encoding="utf-8")
)
STORE = "/api/v1/store"

# Champs que le front lit (docs/BACKEND.md §3 + src/components)
CONTRACT_FIELDS = {
    "id",
    "slug",
    "brand",
    "name",
    "displayName",
    "cardLine",
    "price",
    "categories",
    "summary",
    "highlights",
    "ingredients",
    "usage",
    "benefits",
    "skinTypes",
    "stock",
    "cardImage",
    "mainImage",
    "galleryImages",
    "image",
    "sceneImage",
    "hoverImage",
}


def filename(image):
    return image["src"].rsplit("/", 1)[-1] if image else None


@pytest.fixture
def imported(db):
    call_command("import_demo_catalog", stdout=open("/dev/null", "w"))  # noqa: SIM115


@pytest.mark.django_db
def test_categories_au_format_du_front(client, imported):
    response = client.get(f"{STORE}/categories")
    assert response.status_code == 200
    assert response.json() == {"items": [{"id": c["slug"], "label": c["name"]} for c in FIXTURE["categories"]]}


@pytest.mark.django_db
def test_produits_identiques_au_catalogue_local(client, imported):
    items = client.get(f"{STORE}/products").json()["items"]
    assert [p["id"] for p in items] == [p["slug"] for p in FIXTURE["products"]]
    for api, local in zip(items, FIXTURE["products"], strict=True):
        assert set(api) >= CONTRACT_FIELDS, CONTRACT_FIELDS - set(api)
        assert api["id"] == api["slug"] == local["slug"]
        for key in (
            "brand",
            "name",
            "displayName",
            "cardLine",
            "price",
            "categories",
            "summary",
            "highlights",
            "ingredients",
            "usage",
            "benefits",
            "skinTypes",
        ):
            assert api[key] == local[key], (local["slug"], key)
        assert isinstance(api["price"], int)  # 129 et non "129.00"
        gallery = api["galleryImages"]
        assert [filename(g) for g in gallery] == [Path(g["file"]).name for g in local["gallery"]]
        assert [(g["alt"], g["kind"], g["fit"]) for g in gallery] == [
            (g["alt"], g["kind"], g["fit"]) for g in local["gallery"]
        ]
        assert api["cardImage"] == api["mainImage"] == gallery[0]
        assert filename(api["sceneImage"]) == Path(local["scene"]["file"]).name
        assert api["sceneImage"]["src640"].endswith(Path(local["scene"]["file640"]).name)
        assert api["image"] == api["sceneImage"]
        hover = local["hover"]
        assert filename(api["hoverImage"]) == filename(gallery[hover["galleryIndex"]])
        assert api["hoverImage"].get("position", "") == hover["position"]


@pytest.mark.django_db
def test_donnees_sensibles_jamais_publiques(client, imported):
    Variant.objects.update(cost=Decimal("4321.57"), stock_quantity=7)
    raw = client.get(f"{STORE}/products").content.decode()
    assert '"cost"' not in raw and "4321" not in raw
    first = client.get(f"{STORE}/products").json()["items"][0]
    assert first["stock"] is None and first["inStock"] is True
    assert set(first["variants"][0]) == {"id", "title", "price", "compareAtPrice", "available", "isDefault", "options"}


@pytest.mark.django_db
def test_brouillons_et_archives_invisibles(client, imported):
    Product.objects.filter(slug="biovene-eye-patches").update(status="draft")
    Product.objects.filter(slug="baroness-aloe-vera-gel").update(status="archived")
    slugs = [p["id"] for p in client.get(f"{STORE}/products").json()["items"]]
    assert "biovene-eye-patches" not in slugs and "baroness-aloe-vera-gel" not in slugs and len(slugs) == 3
    assert client.get(f"{STORE}/products/biovene-eye-patches").status_code == 404


@pytest.mark.django_db
def test_detail_produit(client, imported):
    data = client.get(f"{STORE}/products/some-by-mi-yuja-niacin-cream").json()
    assert data["displayName"] == "SOME BY MI Yuja Niacin Cream"
    assert data["seo"]["title"] == "SOME BY MI Yuja Niacin Cream"
    response = client.get(f"{STORE}/products/inconnu")
    assert response.status_code == 404 and response.json()["error"]["code"] == "not_found"


@pytest.mark.django_db
def test_categorie_masquee(client, imported):
    Category.objects.filter(slug="eclat").update(is_active=False)
    assert [c["id"] for c in client.get(f"{STORE}/categories").json()["items"]] == ["hydratation", "anti-age"]
    yuja = client.get(f"{STORE}/products/some-by-mi-yuja-niacin-cream").json()
    assert yuja["categories"] == []


@pytest.mark.django_db
def test_api_publique_sans_session_ni_csrf_et_lecture_seule(client, imported):
    assert client.get(f"{STORE}/products").status_code == 200
    assert client.post(f"{STORE}/products", {}, format="json").status_code == 405


@pytest.mark.django_db
def test_rupture_de_stock(client, imported):
    Variant.objects.filter(product__slug="biovene-eye-patches").update(track_inventory=True, stock_quantity=0)
    data = client.get(f"{STORE}/products/biovene-eye-patches").json()
    assert data["inStock"] is False and data["variants"][0]["available"] is False


@pytest.mark.django_db
def test_import_idempotent_et_mise_a_jour(imported):
    call_command("import_demo_catalog", stdout=open("/dev/null", "w"))  # noqa: SIM115
    assert Product.objects.count() == 5 and Variant.objects.count() == 5
    Product.objects.filter(slug="biovene-eye-patches").update(brand="Modifiée")
    call_command("import_demo_catalog", stdout=open("/dev/null", "w"))  # noqa: SIM115
    assert Product.objects.get(slug="biovene-eye-patches").brand == "Modifiée"  # jamais écrasé par défaut
    call_command("import_demo_catalog", "--update", stdout=open("/dev/null", "w"))  # noqa: SIM115
    assert Product.objects.get(slug="biovene-eye-patches").brand == "BIOVÈNE"
    assert Product.objects.filter(status="active").count() == 5
