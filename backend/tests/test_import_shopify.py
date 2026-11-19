"""Import Shopify → Jodhur : brouillons, fournisseur, variantes, stock, sans doublon ni écrasement."""

import json

import pytest
from django.core.management import call_command

from apps.accounts.roles import Role
from apps.catalog.management.commands import import_shopify
from apps.catalog.models import Product, Variant
from apps.inventory.models import StockMovement
from tests.conftest import image_bytes

IMG = "https://cdn.shopify.com/s/files/1/0000/0001/files/a.png?v=1"


def product(pid=1, handle="baume-rose", title="Baume Rose", **extra):
    data = {
        "id": f"gid://shopify/Product/{pid}",
        "handle": handle,
        "title": title,
        "status": "ACTIVE",
        "vendor": "Coopérative Test",
        "descriptionHtml": "<p>Premier paragraphe.</p><p>Suite <script>x</script></p>",
        "category": "Health & Beauty > Lip Balms",
        "collections": ["Soins"],
        "options": [{"name": "Title", "values": ["Default Title"]}],
        "images": [{"url": IMG, "alt": None, "width": 10, "height": 10}],
        "variants": [
            {
                "id": f"gid://shopify/ProductVariant/{pid}0",
                "title": "Default Title",
                "sku": None,
                "price": "20.00",
                "compareAtPrice": "30.00",
                "inventoryQuantity": 7,
                "tracked": True,
                "options": [{"name": "Title", "value": "Default Title"}],
                "imageUrl": None,
            }
        ],
    }
    data.update(extra)
    return data


def multi(pid=2):
    variants = [
        {
            "id": f"gid://shopify/ProductVariant/{pid}{i}",
            "title": f"{size} / {mat}",
            "sku": sku,
            "price": price,
            "compareAtPrice": None,
            "inventoryQuantity": stock,
            "tracked": True,
            "options": [{"name": "size", "value": size}, {"name": "Matière", "value": mat}],
            "imageUrl": None,
        }
        for i, (size, mat, sku, price, stock) in enumerate(
            [("60ml", "Verre", "EAU-60", "30.00", 4), ("100ml", "Verre", None, "43.00", 0)]
        )
    ]
    return product(
        pid,
        handle="eau-rose",
        title="Eau de Rose",
        options=[{"name": "size", "values": ["60ml", "100ml"]}, {"name": "Matière", "values": ["Verre"]}],
        variants=variants,
    )


@pytest.fixture
def source(tmp_path, monkeypatch):
    monkeypatch.setattr(import_shopify, "_download", lambda url: image_bytes())

    def _write(products):
        path = tmp_path / "shopify.json"
        path.write_text(json.dumps({"source": "test", "products": products}), encoding="utf-8")
        return str(path)

    return _write


def run(path, *args, tmp_path=None):
    call_command("import_shopify", "--source", path, *args)


@pytest.mark.django_db
def test_apercu_n_ecrit_rien(source, tmp_path):
    report = tmp_path / "apercu.md"
    run(source([product(), multi()]), "--dry-run", "--report", str(report))
    assert Product.objects.filter(shopify_id__isnull=False).count() == 0
    text = report.read_text(encoding="utf-8")
    assert "APERÇU" in text and "SKU manquant : 2 variante(s) sur 3" in text and "Coopérative Test" in text


@pytest.mark.django_db
def test_import_brouillon_fournisseur_variantes_stock(source):
    run(source([product(), multi()]))
    p = Product.objects.get(shopify_id="gid://shopify/Product/1")
    assert p.status == "draft" and p.supplier == "Coopérative Test" and p.brand == ""
    assert p.display_name == "Baume Rose" and p.summary == "Premier paragraphe."
    assert "<script" not in p.description_html
    assert p.images.count() == 1
    v = p.variants.get()
    assert (v.price, v.compare_at_price, v.stock_quantity, v.title) == (20, 30, 7, "")
    assert StockMovement.objects.get(variant=v).reason == "initial_count"

    m = Product.objects.get(shopify_id="gid://shopify/Product/2")
    assert [o.name for o in m.options.order_by("position")] == ["Taille", "Matière"]
    vs = list(m.variants.order_by("position"))
    assert [v.sku for v in vs] == ["EAU-60", None] and vs[0].is_default and vs[1].stock_quantity == 0
    assert sorted(ov.value for ov in vs[1].option_values.all()) == ["100ml", "Verre"]


@pytest.mark.django_db
def test_aucun_doublon_et_modifications_locales_conservees(source):
    path = source([product()])
    run(path)
    p = Product.objects.get()
    p.name, p.brand, p.supplier = "Nom modifié", "Ma marque", "Autre"
    p.save()
    v = p.variants.get()
    v.price, v.compare_at_price, v.stock_quantity = 99, None, 2
    v.save()
    run(path)  # 2e exécution
    assert Product.objects.count() == 1
    p.refresh_from_db()
    v.refresh_from_db()
    assert (p.name, p.brand, p.supplier, v.price, v.stock_quantity) == ("Nom modifié", "Ma marque", "Autre", 99, 2)


@pytest.mark.django_db
def test_doublon_local_et_sku_deja_pris(source, sellable, tmp_path):
    local = sellable(slug="baume-rose")
    Variant.objects.filter(product=local).update(sku="EAU-60")
    report = tmp_path / "r.md"
    run(source([product(), multi()]), "--report", str(report))
    assert not Product.objects.filter(shopify_id="gid://shopify/Product/1").exists()  # même slug : non importé
    assert "doublon possible" in report.read_text(encoding="utf-8")
    m = Product.objects.get(shopify_id="gid://shopify/Product/2")
    assert all(v.sku is None for v in m.variants.all())  # SKU déjà utilisé localement : non repris


def test_images_hors_shopify_refusees():
    for url in ("https://evil.example/x.png", "http://cdn.shopify.com/x.png", "file:///etc/passwd"):
        with pytest.raises(ValueError):
            import_shopify._download(url)


@pytest.mark.django_db
def test_refuse_produits_non_actifs(source):
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        run(source([product(status="DRAFT")]))
    assert Product.objects.count() == 0


@pytest.mark.django_db
def test_fournisseur_admin_seulement(source, staff, client, shop):
    run(source([product()]))
    p = Product.objects.get()
    api = staff(Role.ADMIN)
    assert api.get(f"/api/v1/admin/products/{p.pk}").json()["supplier"] == "Coopérative Test"
    assert api.patch(f"/api/v1/admin/products/{p.pk}", {"supplier": "Nouveau"}, format="json").status_code == 200
    assert api.get("/api/v1/admin/products", {"search": "Nouveau"}).json()["items"][0]["supplier"] == "Nouveau"
    # Copie d'un produit importé : pas le même identifiant Shopify.
    from apps.catalog.public import product_payload

    assert "supplier" not in json.dumps(product_payload(p))  # jamais sur la boutique
    copy = api.post(f"/api/v1/admin/products/{p.pk}/duplicate").json()
    assert Product.objects.get(pk=copy["id"]).shopify_id is None
