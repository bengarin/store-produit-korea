"""Catégories besoin (Hydratation, Éclat, Anti-âge) → filtre « Besoin » : aperçu, application, réversibilité."""

import pytest
from django.core.management import call_command

from apps.catalog.models import Category, FilterGroup, FilterOption, ProductCategory


@pytest.fixture
def needs(category):
    eclat = category(slug="eclat", name="Éclat", name_ar="إشراقة")
    anti = category(slug="anti-taches-x", name="Crèmes anti-taches", parent=eclat)
    hyd = category(slug="hydratation", name="Hydratation")
    age = category(slug="anti-age", name="Anti-âge")
    visage = category(slug="visage-x", name="Visage")
    return {"eclat": eclat, "sub": anti, "hyd": hyd, "age": age, "visage": visage}


@pytest.mark.django_db
def test_apercu_n_ecrit_rien(needs, product, tmp_path):
    p = product(slug="serum")
    ProductCategory.objects.create(product=p, category=needs["eclat"])
    report = tmp_path / "a.md"
    call_command("besoins_en_filtres", "--report", str(report))
    assert not FilterGroup.objects.filter(slug="besoin").exists()
    assert Category.objects.get(slug="eclat").is_active
    text = report.read_text(encoding="utf-8")
    assert "**Éclat** (إشراقة) → option `besoin:eclat` — à créer — 1 produit(s)" in text
    assert "/produits?filtres=besoin:eclat" in text


@pytest.mark.django_db
def test_application_conserve_le_classement_et_reste_reversible(needs, product, tmp_path):
    a = product(slug="serum")  # Éclat + Visage
    b = product(slug="creme")  # sous-catégorie Éclat › Crèmes anti-taches seulement
    ProductCategory.objects.filter(product__in=[a, b]).delete()
    ProductCategory.objects.create(product=a, category=needs["eclat"])
    ProductCategory.objects.create(product=a, category=needs["visage"], position=1)
    ProductCategory.objects.create(product=b, category=needs["sub"])
    report = tmp_path / "r.md"
    call_command("besoins_en_filtres", "--report", str(report))
    text = report.read_text(encoding="utf-8")
    assert "Produits sans AUCUNE autre catégorie : **1** sur 2" in text

    call_command("besoins_en_filtres", "--appliquer")
    eclat = FilterOption.objects.get(group__slug="besoin", slug="eclat")
    assert eclat.name == "Éclat" and eclat.name_ar == "إشراقة"
    assert set(eclat.products.all()) == {a, b}  # sous-catégorie → filtre du besoin parent
    assert not Category.objects.get(slug="eclat").is_active and not Category.objects.get(slug="anti-taches-x").is_active
    assert Category.objects.get(slug="visage-x").is_active  # autres catégories intactes
    assert ProductCategory.objects.filter(product=a, category=needs["eclat"]).exists()  # liens gardés
    call_command("besoins_en_filtres", "--appliquer")  # rejouable sans doublon
    assert FilterOption.objects.filter(group__slug="besoin").count() == 3 and eclat.products.count() == 2


@pytest.mark.django_db
def test_signale_liens_de_la_banniere_et_filtres_ressemblants(needs, tmp_path):
    from apps.themes.models import HeroSlide

    HeroSlide.objects.create(
        position=0, title_fr="Promo", button_link="/produits?categorie=eclat", desktop_asset="hero-wide"
    )
    group = FilterGroup.objects.create(slug="mes-solutions", name="Mes Solutions")
    FilterOption.objects.create(group=group, slug="anti-taches", name="Anti-taches & éclat")
    report = tmp_path / "r.md"
    call_command("besoins_en_filtres", "--report", str(report))
    text = report.read_text(encoding="utf-8")
    assert "bannière d'accueil « Promo » : lien « /produits?categorie=eclat »" in text
    assert "« Mes Solutions › Anti-taches & éclat » ↔ besoin « Éclat »" in text
    assert "↔ besoin « Anti-âge »" not in text


@pytest.mark.django_db
def test_categorie_inconnue_refusee(needs):
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("besoins_en_filtres", "--categories", "eclat,inexistante", "--appliquer")
    assert Category.objects.get(slug="eclat").is_active
