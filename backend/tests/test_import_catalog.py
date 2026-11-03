"""Import des 6 produits (backend/catalog_import) : aperçu sans écriture, idempotence, prix et stock protégés."""

from decimal import Decimal
from io import StringIO

import pytest
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


@pytest.fixture
def categories(db):
    for i, (slug, name) in enumerate([("hydratation", "Hydratation"), ("anti-age", "Anti-âge"), ("eclat", "Éclat")]):
        Category.objects.get_or_create(slug=slug, defaults={"name": name, "position": i})


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
def test_apercu_n_ecrit_rien(categories):
    before = counts()
    text = run("--dry-run")
    assert counts() == before
    assert "APERÇU" in text and text.count("À définir") == 6


@pytest.mark.django_db
def test_import_complet_et_idempotent(categories):
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
    eye = Product.objects.get(slug="vitamin-collagen-vital-eye-cream")
    assert eye.images.filter(in_gallery=True).count() == 3 and eye.marketing_images.count() == 3
    assert ProductMarketingImage.objects.count() == 19

    text = run()  # 2e passage : aucun doublon, rien à modifier
    assert counts() == first
    assert "masquée" not in text
    assert "lien créé" not in text and "— créé" not in text


@pytest.mark.django_db
def test_stock_arabe_et_photo_masquee(categories):
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
