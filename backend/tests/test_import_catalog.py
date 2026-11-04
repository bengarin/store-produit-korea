"""Import des 6 produits (backend/catalog_import) : aperçu sans écriture, idempotence, prix et stock protégés."""

import importlib
import json
from decimal import Decimal
from io import StringIO

import pytest
from django.conf import settings
from django.core.management import CommandError, call_command

from apps.catalog.models import Category, Product, ProductHighlight, ProductImage, ProductMarketingImage, Variant
from apps.media_library.models import MediaAsset

SLUGS = {
    "baroness-aloe-vera-gel",
    "some-by-mi-yuja-niacin-cream",
    "biovene-eye-patches",
    "vitamin-collagen-vital-cream",
    "vitamin-collagen-vital-eye-cream",
    "orjena-power-collagen-emulsion",
}


# Catégories exigées par catalogue.json : créées par la migration catalog 0006 (aucun fixture ici).
BASE_CATEGORIES = {"hydratation": "Hydratation", "anti-age": "Anti-âge", "eclat": "Éclat"}
# Photos en galerie et visuels marketing attendus par produit (catalogue.json).
# Par produit : (photos en galerie, visuels FR affichés, visuels AR affichés, visuels AR masqués).
EXPECTED_MEDIA = {
    "baroness-aloe-vera-gel": (3, 3, 1, 1),
    "some-by-mi-yuja-niacin-cream": (4, 3, 3, 0),
    "biovene-eye-patches": (5, 4, 3, 0),
    "vitamin-collagen-vital-cream": (2, 4, 3, 0),
    "vitamin-collagen-vital-eye-cream": (3, 3, 3, 0),
    "orjena-power-collagen-emulsion": (3, 4, 3, 1),
}


@pytest.mark.django_db
def test_categories_creees_par_migrate():
    # Base « sans catégories », puis vraie exécution de `migrate` : la migration catalog 0006 les recrée.
    Category.objects.filter(slug__in=BASE_CATEGORIES).delete()
    call_command("migrate", "catalog", "0005", verbosity=0)
    assert not Category.objects.filter(slug__in=BASE_CATEGORIES).exists()
    call_command("migrate", verbosity=0)
    rows = list(Category.objects.filter(slug__in=BASE_CATEGORIES).values_list("slug", "name"))
    assert dict(rows) == BASE_CATEGORIES
    assert len(rows) == 3  # une seule ligne par slug
    assert Category.objects.filter(slug__in=BASE_CATEGORIES, is_active=True).count() == 3


@pytest.mark.django_db
def test_migration_des_categories_rejouable_sans_doublon():
    from django.apps import apps as django_apps

    migration = importlib.import_module("apps.catalog.migrations.0006_seed_categories")
    Category.objects.filter(slug="eclat").update(name="Éclat (renommée dans l'admin)")
    migration.create_categories(django_apps, None)
    migration.create_categories(django_apps, None)
    assert Category.objects.filter(slug__in=BASE_CATEGORIES).count() == 3
    assert Category.objects.get(slug="eclat").name == "Éclat (renommée dans l'admin)"  # jamais écrasée


def run(*args):
    out = StringIO()
    call_command("import_catalog", *args, stdout=out)
    return out.getvalue()


def counts():
    return (
        Product.objects.count(),
        Variant.objects.count(),
        ProductImage.objects.count(),
        ProductMarketingImage.objects.count(),
        MediaAsset.objects.count(),
    )


@pytest.mark.django_db
def test_apercu_n_ecrit_rien(db):
    before = counts()
    text = run("--dry-run")
    assert counts() == before
    assert "APERÇU" in text and text.count("à définir (0 DH)") == 6  # nouveaux produits : prix à définir


@pytest.mark.django_db
def test_import_complet_et_idempotent(db):
    run()
    assert set(Product.objects.values_list("slug", flat=True)) == SLUGS
    first = counts()
    for p in Product.objects.all():
        assert p.status == Product.Status.DRAFT  # en attente de tarification
        v = p.variants.get(is_default=True)
        assert v.price == Decimal("0") and v.compare_at_price is None
        assert v.stock_quantity is None  # jamais inventé
        assert p.images.filter(in_gallery=True).exists()
        assert not p.marketing_images.filter(category="before_after").exists()
    for slug, (photos, fr, ar, ar_hidden) in EXPECTED_MEDIA.items():
        p = Product.objects.get(slug=slug)
        assert p.images.filter(in_gallery=True).count() == photos, slug
        assert p.marketing_images.filter(language="fr", is_active=True).count() == fr, slug
        assert p.marketing_images.filter(language="ar", is_active=True).count() == ar, slug
        assert p.marketing_images.filter(language="ar", is_active=False).count() == ar_hidden, slug
        assert all(i.media.file and (settings.MEDIA_ROOT / i.media.file.name).is_file() for i in p.images.all())
    assert ProductMarketingImage.objects.count() == 39  # 21 FR + 18 AR
    assert set(Product.objects.values_list("categories__slug", flat=True)) == set(BASE_CATEGORIES)

    text = run()  # 2e passage : aucun doublon, rien à modifier
    assert counts() == first
    assert "masquée" not in text
    assert "lien créé" not in text and "— créé" not in text


@pytest.mark.django_db
def test_produit_existant_jamais_modifie_depuis_le_catalogue(db):
    """Prix, stock, statut, textes français (admin), pictos, photos : la base est conservée telle quelle."""
    run()
    vital = Product.objects.get(slug="vitamin-collagen-vital-cream")
    v = vital.variants.get(is_default=True)
    Variant.objects.filter(pk=v.pk).update(price=Decimal("229"), stock_quantity=7)
    Product.objects.filter(pk=vital.pk).update(
        summary="Texte modifié dans l'admin", summary_ar="نص عربي", status="active"
    )
    vital.highlights.filter(position=0).update(label="Picto modifié")
    extra_media = MediaAsset.objects.filter(product_images__product__slug="vitamin-collagen-vital-eye-cream").first()
    extra = ProductImage.objects.create(product=vital, media=extra_media, alt="Photo ajoutée dans l'admin", position=9)
    first = vital.images.order_by("position").first()
    ProductImage.objects.filter(pk=first.pk).update(alt="Texte alternatif modifié")

    text = run()
    vital.refresh_from_db()
    v.refresh_from_db()
    assert v.stock_quantity == 7 and v.price == Decimal("229") and vital.status == Product.Status.ACTIVE
    assert vital.summary == "Texte modifié dans l'admin" and vital.summary_ar == "نص عربي"
    assert vital.highlights.get(position=0).label == "Picto modifié"
    extra.refresh_from_db()
    assert extra.in_gallery is True  # jamais masquée
    assert ProductImage.objects.get(pk=first.pk).alt == "Texte alternatif modifié"
    assert "Français conservé" in text and "summary" in text and "pictos" in text
    assert "conservée telle quelle" in text


# --- Import complet : traductions arabes (traductions/traductions_ar_6_produits.json) ---------------------
TRANSLATIONS = settings.BASE_DIR.parent / "traductions" / "traductions_ar_6_produits.json"


def translations(tmp_path, status="valide", edit=None):
    data = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))
    for row in data["produits"]:
        row["content_status"] = status
    if edit:
        edit(data)
    path = tmp_path / "trad.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(path), {r["slug"]: r for r in data["produits"]}


def snapshot():
    return (
        list(Product.objects.order_by("pk").values()),
        list(ProductHighlight.objects.order_by("pk").values()),
        list(Variant.objects.order_by("pk").values()),
        list(Category.objects.order_by("pk").values()),
    )


@pytest.mark.django_db
def test_traductions_validees_importees_avec_le_catalogue(tmp_path):
    path, rows = translations(tmp_path)
    run("--traductions", path)
    p = Product.objects.get(slug="baroness-aloe-vera-gel")
    row = rows[p.slug]
    assert p.display_name_ar == row["display_name_ar"] and p.usage_steps_ar == row["usage_steps_ar"]
    assert p.ingredients == row["ingredients"] and p.usage_steps == row["usage_steps"]  # français optimisé
    assert p.summary == row["source_fr"]["summary"]  # le reste du français reste celui du catalogue
    assert [h.label_ar for h in p.highlights.order_by("position")] == row["highlights_ar"]
    assert p.highlights.count() == 4  # aucun doublon de picto
    assert Category.objects.get(slug="eclat").name_ar == ""  # bloc catégories encore « proposition »
    first = snapshot()
    text = run("--traductions", path)  # 2e passage : rien à modifier
    assert snapshot() == first and "| IMPORTÉ |" not in text


@pytest.mark.django_db
def test_dry_run_complet_n_ecrit_rien_et_montre_les_champs(tmp_path):
    run()
    before = snapshot()
    path, _ = translations(tmp_path)
    text = run("--traductions", path, "--dry-run")
    assert snapshot() == before
    assert "APERÇU" in text and "| summary_ar |" in text and "| ingredients (FR optimisé) |" in text
    assert "| IMPORTÉ |" in text and "Traduction : validée" in text


@pytest.mark.django_db
def test_traduction_non_validee_jamais_importee(tmp_path):
    path, _ = translations(tmp_path, status="proposition")
    text = run("--traductions", path)
    assert "non importée" in text
    assert not Product.objects.exclude(summary_ar="").exists()
    p = Product.objects.get(slug="baroness-aloe-vera-gel")
    assert p.ingredients == ["Aloe vera — pureté de 99,85 % selon l'emballage"]  # français du catalogue


@pytest.mark.django_db
def test_conflit_francais_traduction_refuse(tmp_path):
    def edit(data):
        data["produits"][0]["source_fr"]["summary"] = "Ancien texte traduit."

    path, rows = translations(tmp_path, edit=edit)
    text = run("--traductions", path)
    slug = next(iter(rows))
    assert "CONFLIT" in text and Product.objects.get(slug=slug).summary_ar == ""
    assert Product.objects.exclude(slug=slug).exclude(summary_ar="").count() == 5  # les autres sont importés


@pytest.mark.django_db
def test_prix_stock_statut_jamais_modifies(tmp_path):
    run()
    Variant.objects.filter(is_default=True).update(
        price=Decimal("150"), compare_at_price=Decimal("180"), stock_quantity=4
    )
    Product.objects.update(status="active")
    path, _ = translations(tmp_path)
    run("--traductions", path)
    assert set(Variant.objects.values_list("price", "compare_at_price", "stock_quantity")) == {
        (Decimal("150"), Decimal("180"), 4)
    }
    assert set(Product.objects.values_list("status", flat=True)) == {"active"}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "edit,message",
    [
        (lambda d: d["produits"].append(dict(d["produits"][0])), "en double"),
        (lambda d: d["produits"][0].update(slug="inconnu"), "absent du catalogue"),
        (lambda d: d["produits"][0].update(highlights_ar=["un seul"]), "highlights_ar"),
        (lambda d: d["produits"][0].update(short_description_ar="ا" * 161), "trop long"),
    ],
)
def test_fichier_de_traductions_invalide_rien_n_est_ecrit(tmp_path, edit, message):
    path, _ = translations(tmp_path, edit=edit)
    with pytest.raises(CommandError, match=message):
        run("--traductions", path)
    assert not Product.objects.filter(slug__in=SLUGS).exists()


@pytest.mark.django_db
def test_francais_modifie_dans_l_admin_bloque_seulement_sa_traduction(tmp_path):
    run()
    Product.objects.filter(slug="baroness-aloe-vera-gel").update(summary="Résumé réécrit dans l'admin.")
    path, rows = translations(tmp_path)
    text = run("--traductions", path)
    p = Product.objects.get(slug="baroness-aloe-vera-gel")
    assert p.summary == "Résumé réécrit dans l'admin."  # jamais remplacé
    assert p.summary_ar == ""  # sa traduction ne correspond plus : non écrite
    assert p.display_name_ar == rows[p.slug]["display_name_ar"]  # les autres champs sont importés
    assert "CONFLIT" in text


@pytest.mark.django_db
def test_simulation_de_validation_uniquement_en_apercu(tmp_path):
    run()
    before = snapshot()
    path, _ = translations(tmp_path, status="proposition")
    with pytest.raises(CommandError, match="--dry-run"):
        run("--traductions", path, "--simuler-valide")
    text = run("--traductions", path, "--dry-run", "--simuler-valide")
    assert "SIMULATION" in text and "| IMPORTÉ |" in text
    assert snapshot() == before
