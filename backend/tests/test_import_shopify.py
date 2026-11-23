"""Import Shopify → Jodhur : brouillons, fournisseur, variantes, stock, sans doublon ni écrasement."""

import json

import pytest
from django.core.management import call_command

from apps.accounts.roles import Role
from apps.catalog.management.commands import import_shopify
from apps.catalog.models import Collection, Product, Variant
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
    assert p.status == "draft" and p.supplier == "Coopérative Test" and p.brand == "Coopérative Test"
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
    assert not Product.objects.filter(shopify_id="gid://shopify/Product/1").exists()  # même slug : non recréé
    assert Product.objects.filter(slug__startswith="baume-rose").count() == 1
    assert "relier + mettre à jour" in report.read_text(encoding="utf-8")  # liaison seulement avec --mettre-a-jour
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


def coll(name, **extra):
    from django.utils.text import slugify

    return Collection.objects.create(slug=slugify(name)[:80] or "c", name=name, **extra)


@pytest.mark.django_db
def test_collections_reliees_si_nom_identique_sans_en_creer(source, tmp_path):
    soins = coll("SOINS")  # majuscules / accents ignorés
    chine = coll("Éclat", required_origin="CN")  # règle d'entrée non remplie par un produit importé
    report = tmp_path / "r.md"
    run(source([product(collections=["Soins", "Eclat", "Coffrets cadeaux"])]), "--report", str(report))
    p = Product.objects.get()
    assert list(p.collections.all()) == [soins] and chine.products.count() == 0
    assert Collection.objects.count() == 2  # aucune collection créée
    text = report.read_text(encoding="utf-8")
    assert "| Coffrets cadeaux | 1 | — | à traiter : aucune collection Jodhur de ce nom |" in text
    assert "pays de fabrication" in text and p.brand == "Coopérative Test" and p.supplier == "Coopérative Test"


@pytest.mark.django_db
def test_collection_ambigue_non_reliee(source):
    coll("Soins")
    Collection.objects.create(slug="soins-2", name="soins")
    run(source([product()]))
    assert Product.objects.get().collections.count() == 0


@pytest.mark.django_db
def test_mise_a_jour_deja_importe_sans_ecraser(source, tmp_path):
    run(source([product(collections=[], vendor="")]))  # import ancien : pas de fournisseur dans Shopify
    p = Product.objects.get()
    p.brand, p.name = "Ma marque", "Nom modifié"
    p.save()
    v = p.variants.get()
    v.price, v.compare_at_price = 99, None
    v.save()
    soins = coll("Soins")
    path = source([product()])
    report = tmp_path / "a.md"
    run(path, "--dry-run", "--mettre-a-jour", "--report", str(report))  # aperçu : rien n'est écrit
    p.refresh_from_db()
    assert p.supplier == "" and p.collections.count() == 0
    text = report.read_text(encoding="utf-8")
    assert "fournisseur → « Coopérative Test »" in text and "collection + « Soins »" in text

    run(path)  # sans --mettre-a-jour : produits existants non touchés
    p.refresh_from_db()
    assert p.supplier == "" and p.collections.count() == 0

    run(path, "--mettre-a-jour")
    p.refresh_from_db()
    v.refresh_from_db()
    assert p.supplier == "Coopérative Test" and list(p.collections.all()) == [soins]
    assert (p.brand, p.name, v.price, Product.objects.count()) == ("Ma marque", "Nom modifié", 99, 1)


@pytest.mark.django_db
def test_fournisseur_local_et_retraits_manuels_respectes(source, tmp_path):
    soins = coll("Soins")
    path = source([product()])
    run(path)
    p = Product.objects.get()
    assert list(p.collections.all()) == [soins]
    p.supplier = "Fournisseur corrigé"
    p.save()
    p.collections.remove(soins)  # retrait manuel
    report = tmp_path / "r.md"
    run(path, "--mettre-a-jour", "--report", str(report))
    p.refresh_from_db()
    assert p.supplier == "Fournisseur corrigé" and p.collections.count() == 0
    text = report.read_text(encoding="utf-8")
    assert "fournisseur local « Fournisseur corrigé » conservé" in text and "retirée à la main" in text

    p.supplier = ""  # effacé à la main après l'import : pas remis
    p.save()
    run(path, "--mettre-a-jour")
    p.refresh_from_db()
    assert p.supplier == ""


@pytest.mark.django_db
def test_liaison_produit_local_par_identifiant_url(source, sellable):
    local = sellable(slug="baume-rose")
    price = local.variants.get().price
    soins = coll("Soins")
    run(source([product()]), "--mettre-a-jour")
    local.refresh_from_db()
    assert local.shopify_id == "gid://shopify/Product/1" and local.supplier == "Coopérative Test"
    assert list(local.collections.all()) == [soins] and local.status == "active"
    assert local.variants.get().price == price and local.brand == "Marque"  # marque saisie : conservée
    assert Product.objects.count() == 1


@pytest.mark.django_db
def test_liaison_ambigue_refusee(source, sellable, tmp_path):
    local = sellable(slug="baume-rose")
    report = tmp_path / "r.md"
    twins = [product(), product(pid=3, handle="baume-rose-2", vendor="Autre")]  # même nom dans Shopify
    run(source(twins), "--mettre-a-jour", "--report", str(report))
    local.refresh_from_db()
    assert local.shopify_id is None and local.supplier == ""  # pas relié : on ne devine pas lequel
    assert "correspondance ambiguë" in report.read_text(encoding="utf-8")


@pytest.mark.django_db
def test_categorie_ajoutee_aux_produits_deja_importes_sans_categorie(source, category, tmp_path):
    path = source([product(collections=["Soins Corps", "Mes Solutions"])])
    run(path)  # import ancien : aucune catégorie Jodhur de ce nom à l'époque
    p = Product.objects.get()
    assert p.categories.count() == 0
    corps = category(slug="soins-corps", name="Soins corps")  # même nom (majuscules ignorées)
    category(slug="soins", name="Soins")  # nom proche : jamais proposé
    report, csv_path = tmp_path / "a.md", tmp_path / "a.csv"
    run(path, "--dry-run", "--mettre-a-jour", "--report", str(report), "--csv", str(csv_path))
    assert p.categories.count() == 0  # aperçu : rien n'est écrit
    text = report.read_text(encoding="utf-8")
    assert "## Prévisualisation détaillée par produit" in text
    assert "| Soins Corps, Mes Solutions | Lip Balms | aucune | Soins corps | catégorie + « Soins corps » |" in text
    assert "categorie_jodhur_proposee" in csv_path.read_text(encoding="utf-8-sig")

    run(path, "--mettre-a-jour")
    assert list(p.categories.all()) == [corps] and p.brand == "Coopérative Test"
    run(path, "--dry-run", "--mettre-a-jour")  # 2e passage : plus rien à faire
    p.categories.clear()  # retrait manuel après l'import
    report2 = tmp_path / "b.md"
    run(path, "--mettre-a-jour", "--report", str(report2))
    assert p.categories.count() == 0 and "retirée(s) à la main" in report2.read_text(encoding="utf-8")


@pytest.mark.django_db
def test_categorie_choisie_dans_jodhur_conservee(source, category, tmp_path):
    path = source([product(collections=["Soins Corps"])])
    run(path)
    p = Product.objects.get()
    mine = category(slug="baumes", name="Baumes")
    p.categories.add(mine)
    category(slug="soins-corps", name="Soins Corps")
    report = tmp_path / "r.md"
    run(path, "--mettre-a-jour", "--report", str(report))
    assert list(p.categories.all()) == [mine]
    assert "déjà choisie(s) dans Jodhur conservée(s)" in report.read_text(encoding="utf-8")


@pytest.mark.django_db
def test_categorie_ambigue_non_proposee(source, category):
    path = source([product(collections=["Soins Corps"])])
    run(path)
    category(slug="soins-corps", name="Soins Corps")
    category(slug="soins-corps-2", name="Soins corps")  # deux catégories de ce nom : on ne choisit pas
    run(path, "--mettre-a-jour")
    assert Product.objects.get().categories.count() == 0


def _mapping(tmp_path, rows):
    import csv

    path = tmp_path / "corresp.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(import_shopify.MAPPING_HEADER)
        for name, value in rows:
            w.writerow([name, "collection", "", "", "", value])
    return str(path)


@pytest.mark.django_db
def test_modele_de_correspondances_sans_ecriture(source, category, tmp_path):
    category(slug="soins-corps", name="Soins Corps")
    out = tmp_path / "corresp.csv"
    run(source([product(collections=["Soins Corps", "Mes Solutions"])]), "--modele-correspondances", str(out))
    assert Product.objects.count() == 0  # rien n'est importé
    text = out.read_text(encoding="utf-8-sig")
    assert "collection_shopify;type;produits" in text
    assert "Soins Corps;collection;1;Baume Rose;soins-corps;" in text and "Mes Solutions;collection;1;" in text
    cats = (tmp_path / "corresp_categories_jodhur.csv").read_text(encoding="utf-8-sig")
    assert "soins-corps;Soins Corps" in cats


@pytest.mark.django_db
def test_correspondances_appliquees_seulement_avec_mise_a_jour(source, category, tmp_path):
    path = source([product(collections=["Soins Corps", "Mes Solutions"])])
    run(path)
    p = Product.objects.get()
    corps = category(slug="corps", name="Corps")
    visage = category(slug="visage", name="Visage")
    corresp = _mapping(tmp_path, [("Soins Corps", "corps"), ("Mes Solutions", "visage | corps")])
    report = tmp_path / "a.md"
    run(path, "--dry-run", "--mettre-a-jour", "--correspondances", corresp, "--report", str(report))
    assert p.categories.count() == 0
    text = report.read_text(encoding="utf-8")
    assert "« Soins Corps » → Corps (1 produit(s), tableau)" in text
    assert "catégorie + « Corps »; catégorie + « Visage »" in text
    run(path, "--mettre-a-jour", "--correspondances", corresp)
    assert set(p.categories.all()) == {corps, visage}


@pytest.mark.django_db
def test_correspondance_aucune_bloque_le_nom_identique(source, category, tmp_path):
    path = source([product(collections=["Soins Corps"])])
    run(path)
    category(slug="soins-corps", name="Soins Corps")
    run(path, "--mettre-a-jour", "--correspondances", _mapping(tmp_path, [("Soins Corps", "aucune")]))
    assert Product.objects.get().categories.count() == 0


@pytest.mark.django_db
def test_tableau_errone_refuse_sans_rien_ecrire(source, tmp_path):
    from django.core.management.base import CommandError

    corresp = _mapping(tmp_path, [("Soins", "inexistante"), ("Pas dans Shopify", "")])
    with pytest.raises(CommandError, match="inexistante"):
        run(source([product()]), "--correspondances", corresp)
    assert Product.objects.count() == 0


@pytest.mark.django_db
def test_marque_completee_si_vide_et_marque_saisie_conservee(source, tmp_path):
    old = source([product(vendor=""), product(pid=4, handle="savon", title="Savon")])
    run(old)  # import ancien : Vendor vide → marque et fournisseur vides
    a = Product.objects.get(shopify_id="gid://shopify/Product/1")
    b = Product.objects.get(shopify_id="gid://shopify/Product/4")
    Product.objects.filter(pk=a.pk).update(brand="")
    Product.objects.filter(pk=b.pk).update(brand="Ma marque")  # saisie à la main
    path = source([product(vendor="Rouh Ennabta"), product(pid=4, handle="savon", title="Savon")])
    report, csv_path = tmp_path / "a.md", tmp_path / "a.csv"
    run(path, "--dry-run", "--mettre-a-jour", "--report", str(report), "--csv", str(csv_path))
    a.refresh_from_db()
    assert a.brand == ""  # aperçu : rien n'est écrit
    text = report.read_text(encoding="utf-8")
    assert "| Baume Rose | `baume-rose` | Rouh Ennabta | (vide) | Rouh Ennabta |" in text
    assert "marque locale « Ma marque » conservée (Vendor Shopify : « Coopérative Test »)" in text
    assert "marque_proposee" in csv_path.read_text(encoding="utf-8-sig")

    run(path, "--mettre-a-jour")
    a.refresh_from_db()
    b.refresh_from_db()
    assert (a.brand, a.supplier) == ("Rouh Ennabta", "Rouh Ennabta") and b.brand == "Ma marque"

    Product.objects.filter(pk=a.pk).update(brand="")  # effacée à la main après l'import : pas remise
    run(path, "--mettre-a-jour")
    a.refresh_from_db()
    assert a.brand == ""
