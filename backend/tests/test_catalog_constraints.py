"""Contraintes appliquées PAR MYSQL (pas seulement par le code Python)."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from apps.catalog.models import Category, Product, ProductCategory, ProductImage, Variant


def assert_db_refuses(fn):
    with pytest.raises(IntegrityError), transaction.atomic():
        fn()


@pytest.mark.django_db
def test_prix_negatif_refuse_par_la_base(product):
    v = product().variants.get()
    assert_db_refuses(lambda: Variant.objects.filter(pk=v.pk).update(price=Decimal("-1")))


@pytest.mark.django_db
def test_prix_barre_doit_etre_superieur(product):
    v = product().variants.get()
    assert_db_refuses(lambda: Variant.objects.filter(pk=v.pk).update(compare_at_price=Decimal("100")))
    Variant.objects.filter(pk=v.pk).update(compare_at_price=Decimal("150"))  # 150 > 129 : accepté


@pytest.mark.django_db
def test_stock_negatif_seulement_si_vente_sans_stock(product):
    v = product().variants.get()
    assert_db_refuses(lambda: Variant.objects.filter(pk=v.pk).update(stock_quantity=-1))
    Variant.objects.filter(pk=v.pk).update(allow_backorder=True, stock_quantity=-1)


@pytest.mark.django_db
def test_cout_negatif_refuse(product):
    v = product().variants.get()
    assert_db_refuses(lambda: Variant.objects.filter(pk=v.pk).update(cost=Decimal("-5")))


@pytest.mark.django_db
def test_sku_et_slug_uniques(product):
    a, b = product(slug="a"), product(slug="b")
    Variant.objects.filter(product=a).update(sku="SKU-1")
    assert_db_refuses(lambda: Variant.objects.filter(product=b).update(sku="SKU-1"))
    assert_db_refuses(lambda: Product.objects.create(slug="a", brand="x", name="y"))
    # Plusieurs variantes SANS SKU restent possibles (NULL n'est pas un doublon).
    Variant.objects.filter(product=a).update(sku=None)


@pytest.mark.django_db
def test_categorie_utilisee_protegee_et_lien_unique(product):
    p = product()
    cat = p.categories.get()
    with pytest.raises(ProtectedError):
        cat.delete()
    assert_db_refuses(lambda: ProductCategory.objects.create(product=p, category=cat))


@pytest.mark.django_db
def test_media_utilise_protege(product):
    image = ProductImage.objects.get(product=product())
    with pytest.raises(ProtectedError):
        image.media.delete()


@pytest.mark.django_db
def test_suppression_produit_supprime_ses_variantes_images_mais_garde_les_medias(product):
    p = product()
    media = p.images.get().media
    p.delete()
    assert not Variant.objects.exists() and not ProductImage.objects.exists()
    media.refresh_from_db()  # le fichier reste dans la médiathèque


@pytest.mark.django_db
def test_sous_categorie_survit_a_sa_parente(category):
    parent = category(slug="soins", name="Soins")
    child = category(slug="serums", name="Sérums", parent=parent)
    parent.delete()
    child.refresh_from_db()
    assert child.parent is None
    assert Category.objects.count() == 1
