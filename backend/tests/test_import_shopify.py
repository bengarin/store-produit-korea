"""
Import Shopify complet (une seule commande) : aperçu sans écriture, création active, produit bloqué expliqué,
images locales sans doublon, metafields, variantes, correspondances explicites, relance sans doublon,
modifications manuelles conservées.
"""

import csv
import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.catalog.management.commands import import_shopify
from apps.catalog.models import Product, ProductImage, ProductMetafield, Variant
from apps.catalog.shopify_import import source as src
from apps.inventory.models import StockMovement
from tests.conftest import image_bytes

IMG = "https://cdn.shopify.com/s/files/1/0000/0001/files/{}.png?v=1"


def page(items):
    return {"pageInfo": {"hasNextPage": False}, "nodes": items}


def mf(namespace, key, type_, value, i=1):
    return {
        "id": f"gid://shopify/Metafield/{i}{key}",
        "namespace": namespace,
        "key": key,
        "type": type_,
        "value": value,
    }


def rich(*paragraphs):
    return json.dumps(
        {
            "type": "root",
            "children": [{"type": "paragraph", "children": [{"type": "text", "value": p}]} for p in paragraphs],
        }
    )


def variant(vid, title="Default Title", price="20.00", stock=7, sku=None, barcode=None, options=None, compare=None):
    return {
        "id": f"gid://shopify/ProductVariant/{vid}",
        "title": title,
        "sku": sku,
        "position": 1,
        "price": price,
        "compareAtPrice": compare,
        "inventoryQuantity": stock,
        "inventoryPolicy": "DENY",
        "barcodes": {"nodes": [{"type": "EAN13", "value": barcode}] if barcode else []},
        "selectedOptions": options or [{"name": "Title", "value": "Default Title"}],
        "media": {"nodes": []},
        "inventoryItem": {"tracked": True, "measurement": {"weight": {"unit": "GRAMS", "value": 0}}},
    }


def node(
    pid=1,
    handle="baume-rose",
    title="Baume Rose",
    vendor="Coopérative Test",
    collections=("Soins Corps",),
    images=("a", "b"),
    variants=None,
    metafields=None,
    category="Health & Beauty > Lip Balms",
    **extra,
):
    data = {
        "id": f"gid://shopify/Product/{pid}",
        "handle": handle,
        "title": title,
        "status": "ACTIVE",
        "vendor": vendor,
        "productType": "Soin lèvres",
        "tags": ["zone-levres", "bio"],
        "descriptionHtml": "<p>Premier paragraphe.</p><p>Suite <script>x</script></p>",
        "updatedAt": "2026-11-20T10:00:00Z",
        "category": {"id": "gid://shopify/TaxonomyCategory/x", "fullName": category} if category else None,
        "seo": {"title": f"{title} | Jodhur", "description": "Description SEO."},
        "options": [{"name": "Title", "position": 1, "values": ["Default Title"]}],
        "collections": page(
            [{"id": f"gid://shopify/Collection/{i}", "title": c, "handle": c} for i, c in enumerate(collections)]
        ),
        "media": page(
            [
                {
                    "id": f"gid://shopify/MediaImage/{pid}{n}",
                    "mediaContentType": "IMAGE",
                    "alt": "" if n == "b" else f"Alt {n}",
                    "image": {"url": IMG.format(f"{pid}{n}"), "width": 10, "height": 10, "altText": None},
                }
                for n in images
            ]
        ),
        "metafields": page(
            metafields
            if metafields is not None
            else [
                mf("custom", "ingredients", "rich_text_field", rich("Beurre de karité", "Cire d'abeille")),
                mf("custom", "les_benefices", "rich_text_field", rich("✓ Nourrit\n✓ Protège")),
                mf("custom", "type_de_peau", "single_line_text_field", "Tous types"),
                mf("reviews", "rating", "rating", '{"value":"5.0"}'),
            ]
        ),
        "variants": page(variants or [variant(pid * 10, barcode="6111000000001", sku=f"SKU-{pid}")]),
    }
    for m in data["metafields"]["nodes"]:
        m["id"] = f"gid://shopify/Metafield/{pid}{m['key']}"
    data.update(extra)
    return data


@pytest.fixture
def setup(tmp_path, monkeypatch, category):
    """Export + tableau de correspondances (Soins Corps → corps) ; téléchargement d'images simulé."""
    corps = category(slug="corps", name="Corps")
    downloads = []

    def fake_download(url, attempts=3, timeout=30):
        downloads.append(url)
        color = sum(map(ord, url)) % 255
        return image_bytes(color=(color, 120, 40))

    monkeypatch.setattr(import_shopify, "download", fake_download)
    mapping = tmp_path / "corresp.csv"
    with mapping.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(import_shopify.MAPPING_HEADER)
        w.writerow(["Soins Corps", "collection", "", "", "", "corps", "sûr", ""])
        w.writerow(["Mes Solutions", "collection", "", "", "", "aucune", "aucune catégorie adaptée", ""])

    def write(nodes):
        path = tmp_path / "export.json"
        path.write_text(json.dumps({"source": "test", "products": nodes}), encoding="utf-8")
        return path

    def run(nodes, *args, report=None):
        argv = ["--source", str(write(nodes)), "--correspondances", str(mapping), "--nouvelles-categories", "",
                "--categories-produits", "", "--base-precedente", ""]  # fmt: skip
        if report:
            argv += ["--report", str(report)]
        call_command("import_shopify", *argv, *args)
        return report.read_text(encoding="utf-8") if report else None

    return {"run": run, "corps": corps, "downloads": downloads, "tmp": tmp_path}


@pytest.mark.django_db
def test_apercu_n_ecrit_rien(setup):
    text = setup["run"]([node()], report=setup["tmp"] / "a.md")
    assert Product.objects.count() == 0 and not setup["downloads"]
    assert "APERÇU" in text and "créé actif" in text and "À télécharger : 2" in text


@pytest.mark.django_db
def test_creation_complete_et_active(setup):
    setup["run"]([node()], "--appliquer")
    p = Product.objects.get(shopify_id="gid://shopify/Product/1")
    assert p.status == "active" and p.published_at is not None
    assert (p.brand, p.supplier, p.name, p.summary) == (
        "Coopérative Test",
        "Coopérative Test",
        "Baume Rose",
        "Premier paragraphe.",
    )
    assert "<script" not in p.description_html
    assert (p.seo_title, p.seo_description) == ("Baume Rose | Jodhur", "Description SEO.")
    assert (p.shopify_handle, p.shopify_product_type, p.shopify_category) == (
        "baume-rose",
        "Soin lèvres",
        "Health & Beauty > Lip Balms",
    )
    assert p.shopify_tags == ["zone-levres", "bio"] and p.shopify_collections == ["Soins Corps"]
    assert p.ingredients == ["Beurre de karité", "Cire d'abeille"] and p.benefits == ["Nourrit", "Protège"]
    assert p.skin_types == "Tous types"
    assert list(p.categories.all()) == [setup["corps"]]
    images = list(p.images.order_by("position"))
    assert [i.shopify_media_id for i in images] == ["gid://shopify/MediaImage/1a", "gid://shopify/MediaImage/1b"]
    assert images[0].alt == "Alt a" and images[1].alt == "Baume Rose"  # alt vide → nom du produit
    assert all(i.media.file.name.startswith("uploads/") for i in images)  # fichiers locaux, pas d'URL Shopify
    v = p.variants.get()
    assert (v.sku, v.barcode, v.price, v.stock_quantity) == ("SKU-1", "6111000000001", 20, 7)
    assert StockMovement.objects.get(variant=v).reason == "initial_count"
    assert ProductMetafield.objects.filter(product=p).count() == 4
    assert ProductMetafield.objects.get(product=p, key="rating").value == '{"value":"5.0"}'


@pytest.mark.django_db
def test_produit_bloque_reste_brouillon_avec_le_champ_manquant(setup):
    text = setup["run"](
        [node(collections=("Mes Solutions",), category=None)], "--appliquer", report=setup["tmp"] / "r.md"
    )
    p = Product.objects.get()
    assert p.status == "draft"
    assert "**Baume Rose** (`baume-rose`) : Au moins une catégorie est obligatoire." in text
    assert "aucune correspondance pour : Mes Solutions" in text


@pytest.mark.django_db
def test_relance_sans_doublon(setup):
    nodes = [node(), node(pid=2, handle="savon", title="Savon", images=("a",))]
    setup["run"](nodes, "--appliquer")
    n_dl = len(setup["downloads"])
    text = setup["run"](nodes, "--appliquer", report=setup["tmp"] / "r.md")
    assert len(setup["downloads"]) == n_dl  # rien n'est retéléchargé
    assert Product.objects.count() == 2 and ProductImage.objects.count() == 3 and Variant.objects.count() == 2
    assert ProductMetafield.objects.count() == 8 and "déjà à jour" in text and "créé" not in text.split("## Détail")[1]


@pytest.mark.django_db
def test_modifications_manuelles_conservees(setup):
    from apps.catalog import services

    setup["run"]([node()], "--appliquer")
    p = Product.objects.get()
    p.name, p.seo_title = "Nom à moi", "SEO à moi"
    p.save()
    v = p.variants.get()
    v.price = 25
    v.save()
    p.categories.clear()
    services.change_status(p, "draft", user=_staff())
    changed = node(
        title="Baume Rose v2", variants=[variant(10, price="30.00", stock=9, sku="SKU-1", barcode="6111000000001")]
    )
    text = setup["run"]([changed], "--appliquer", report=setup["tmp"] / "r.md")
    p.refresh_from_db()
    v.refresh_from_db()
    assert (p.name, p.seo_title, p.status, v.price) == ("Nom à moi", "SEO à moi", "draft", 25)
    assert p.display_name == "Baume Rose v2"  # non modifié dans Jodhur → mis à jour
    assert v.stock_quantity == 9  # stock non modifié dans Jodhur → mis à jour (avec mouvement tracé)
    assert StockMovement.objects.filter(variant=v, reason="recount").exists()
    assert p.categories.count() == 0  # catégorie retirée à la main : non remise
    assert "nom modifié(e) dans Jodhur : gardé(e)" in text and "mis en brouillon à la main" in text


@pytest.mark.django_db
def test_metafield_disparu_garde_et_marque(setup):
    setup["run"]([node()], "--appliquer")
    setup["run"](
        [node(metafields=[mf("custom", "type_de_peau", "single_line_text_field", "Tous types")])], "--appliquer"
    )
    p = Product.objects.get()
    assert ProductMetafield.objects.filter(product=p).count() == 4
    assert ProductMetafield.objects.get(product=p, key="rating").in_shopify is False


@pytest.mark.django_db
def test_image_identique_non_dupliquee(setup, monkeypatch):
    monkeypatch.setattr(import_shopify, "download", lambda url, attempts=3, timeout=30: image_bytes())
    setup["run"]([node(images=("a", "b"))], "--appliquer")  # deux médias Shopify, même fichier
    p = Product.objects.get()
    assert p.images.count() == 1 and p.images.get().shopify_media_id == "gid://shopify/MediaImage/1b"


def test_telechargement_nouvelles_tentatives(monkeypatch):
    calls = []

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n):
            return b"img"

    def fake_urlopen(req, timeout):
        calls.append(1)
        if len(calls) < 3:
            raise OSError("réseau")
        return Resp()

    monkeypatch.setattr(import_shopify.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(import_shopify.time, "sleep", lambda s: None)
    assert import_shopify.download(IMG.format("x")) == b"img" and len(calls) == 3
    for url in ("https://evil.example/x.png", "http://cdn.shopify.com/x.png"):
        with pytest.raises(ValueError):
            import_shopify.download(url)


def test_lecture_api_paginee(monkeypatch):
    pages = [
        {"data": {"products": {"pageInfo": {"hasNextPage": True, "endCursor": "c1"}, "nodes": [{"id": 1}]}}},
        {"data": {"products": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": [{"id": 2}]}}},
    ]
    seen = []

    def fake_post(url, token, body):
        seen.append(json.loads(body)["variables"]["after"])
        return pages[len(seen) - 1]

    monkeypatch.setattr(src, "_post_with_retries", fake_post)
    nodes = src.fetch_from_api("boutique.myshopify.com", "jeton", "2026-01", log=lambda m: None)
    assert [n["id"] for n in nodes] == [1, 2] and seen == [None, "c1"]
    with pytest.raises(src.SourceError):
        src.fetch_from_api("evil.example.com", "jeton", "2026-01")


@pytest.mark.django_db
def test_variantes_options_et_prix_barre(setup):
    multi = node(
        variants=[
            variant(11, "30 ml", "30.00", 4, options=[{"name": "size", "value": "30 ml"}], compare="40.00"),
            variant(12, "60 ml", "50.00", 0, options=[{"name": "size", "value": "60 ml"}], compare="10.00"),
        ],
        options=[{"name": "size", "position": 1, "values": ["30 ml", "60 ml"]}],
    )
    setup["run"]([multi], "--appliquer")
    p = Product.objects.get()
    assert [o.name for o in p.options.all()] == ["Taille"]
    v1, v2 = p.variants.order_by("position")
    assert (v1.compare_at_price, v2.compare_at_price) == (40, None)  # prix barré seulement s'il est > prix
    assert v1.is_default and [ov.value for ov in v2.option_values.all()] == ["60 ml"]


@pytest.mark.django_db
def test_refus_produits_non_actifs_et_ancien_format(setup, tmp_path):
    with pytest.raises(CommandError):
        setup["run"]([node(status="DRAFT")])
    old = tmp_path / "old.json"
    old.write_text(json.dumps({"products": [{"id": "x", "status": "ACTIVE", "images": []}]}), encoding="utf-8")
    with pytest.raises(CommandError, match="Ancien format"):
        call_command("import_shopify", "--source", str(old))


@pytest.mark.django_db
def test_donnees_shopify_dans_l_admin_pas_sur_la_boutique(setup, staff):
    from apps.accounts.roles import Role
    from apps.catalog.public import product_payload

    setup["run"]([node()], "--appliquer")
    p = Product.objects.get()
    data = staff(Role.ADMIN).get(f"/api/v1/admin/products/{p.pk}").json()["shopify"]
    assert data["handle"] == "baume-rose" and data["tags"] == ["zone-levres", "bio"]
    assert {m["key"] for m in data["metafields"]} >= {"ingredients", "rating"}
    public = json.dumps(product_payload(p))
    assert "metafield" not in public and "zone-levres" not in public


def _staff():
    from apps.accounts.models import User

    return User.objects.create_user(email="gestion@exemple.ma", password="Mot-de-passe-solide-1", is_staff=True)


@pytest.mark.django_db
def test_categories_utiles_rendues_visibles_avant_activation(setup, tmp_path):
    news = tmp_path / "nouvelles.csv"
    news.write_text(
        "identifiant_url;nom;nom_ar;parente\nsoins;Soins;;\ncorps-x;Corps X;;soins\ninutile;Inutile;;\n",
        encoding="utf-8-sig",
    )
    mapping = tmp_path / "corresp2.csv"
    mapping.write_text(
        ";".join(import_shopify.MAPPING_HEADER) + "\nSoins Corps;collection;;;;corps-x;sûr;\n", encoding="utf-8-sig"
    )
    src_file = tmp_path / "export2.json"
    src_file.write_text(json.dumps({"products": [node(), node(pid=2, handle="x", title="X", collections=())]}))
    args = ["--source", str(src_file), "--correspondances", str(mapping), "--nouvelles-categories", str(news),
            "--categories-produits", "", "--base-precedente", "", "--rendre-visibles", "utiles"]  # fmt: skip
    report = tmp_path / "a.md"
    call_command("import_shopify", *args, "--report", str(report))
    text = report.read_text(encoding="utf-8")
    assert "Soins › Corps X (`corps-x`) : sera rendue visible — 1 produit(s)" in text and "Soins (`soins`)" in text
    assert "Restent masquées (aucun produit actif) : Inutile" in text
    assert "**X** (`x`) : Au moins une catégorie est obligatoire." in text
    from apps.catalog.models import Category

    assert not Category.objects.filter(slug="corps-x").exists()  # aperçu
    call_command("import_shopify", *args, "--appliquer")
    assert Category.objects.get(slug="corps-x").is_active and Category.objects.get(slug="soins").is_active
    assert not Category.objects.get(slug="inutile").is_active
    assert Product.objects.get(slug="baume-rose").status == "active" and Product.objects.get(slug="x").status == "draft"
