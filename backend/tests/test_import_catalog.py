"""Import des 6 produits (backend/catalog_import) : aperçu sans écriture, idempotence, prix et stock protégés."""

import importlib
from decimal import Decimal
from io import StringIO

import pytest
from django.conf import settings
from django.core.management import call_command

from apps.catalog.models import Category, Product, ProductImage, ProductMarketingImage, Variant
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
    "baroness-aloe-vera-gel": (3, 2, 1, 1),
    "some-by-mi-yuja-niacin-cream": (4, 2, 0, 0),
    "biovene-eye-patches": (5, 4, 1, 0),
    "vitamin-collagen-vital-cream": (2, 4, 1, 0),
    "vitamin-collagen-vital-eye-cream": (3, 3, 0, 0),
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
    assert "APERÇU" in text and text.count("À définir") == 6


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
    assert ProductMarketingImage.objects.count() == 27  # 19 FR + 8 AR
    assert set(Product.objects.values_list("categories__slug", flat=True)) == set(BASE_CATEGORIES)

    text = run()  # 2e passage : aucun doublon, rien à modifier
    assert counts() == first
    assert "masquée" not in text
    assert "lien créé" not in text and "— créé" not in text


@pytest.mark.django_db
def test_stock_arabe_et_photo_masquee(db):
    run()
    vital = Product.objects.get(slug="vitamin-collagen-vital-cream")
    v = vital.variants.get(is_default=True)
    Variant.objects.filter(pk=v.pk).update(price=Decimal("229"), stock_quantity=7)
    Product.objects.filter(pk=vital.pk).update(summary="ancien texte", summary_ar="نص عربي", status="active")
    extra_media = MediaAsset.objects.filter(product_images__product__slug="vitamin-collagen-vital-eye-cream").first()
    extra = ProductImage.objects.create(product=vital, media=extra_media, position=9)

    text = run()
    vital.refresh_from_db()
    v.refresh_from_db()
    assert v.stock_quantity == 7  # stock jamais modifié
    assert v.price == 0 and vital.status == Product.Status.DRAFT
    assert vital.summary_ar == "نص عربي"  # arabe jamais effacé
    assert "relire la traduction arabe" in text
    extra.refresh_from_db()
    assert extra.in_gallery is False  # masquée de la galerie, jamais supprimée
    assert MediaAsset.objects.filter(pk=extra_media.pk).exists()
    assert "masquée de la galerie" in text
