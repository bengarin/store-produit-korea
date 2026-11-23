"""Classement des produits Jodhur par zone (filtre « Zone d'application ») et catégories rendues visibles."""

import csv

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.catalog.models import Category, FilterGroup, FilterOption, ProductCategory


@pytest.fixture
def setup(category, product):
    eclat = category(slug="eclat", name="Éclat")
    visage = category(slug="visage", name="Visage", is_active=False)
    category(slug="yeux", name="Yeux", parent=visage, is_active=False)
    zone = FilterGroup.objects.create(slug="zone-dapplication", name="Zone d'application")
    opt_visage = FilterOption.objects.create(group=zone, slug="visage", name="Visage")
    opt_yeux = FilterOption.objects.create(group=zone, slug="yeux", name="Yeux")
    a = product(slug="creme", status="active")
    b = product(slug="contour", status="active")
    c = product(slug="sans-zone", status="active")
    ProductCategory.objects.filter(product__in=[a, b, c]).delete()
    for p in (a, b, c):
        ProductCategory.objects.create(product=p, category=eclat)
    opt_visage.products.add(a)
    opt_yeux.products.add(b)
    return {"visage": visage, "a": a, "b": b, "c": c}


def _read(path):
    with open(path, encoding="utf-8-sig") as fh:
        return {r["identifiant_url"]: r for r in csv.DictReader(fh, delimiter=";")}


@pytest.mark.django_db
def test_modele_propositions_depuis_le_filtre_zone(setup, tmp_path):
    out = tmp_path / "liste.csv"
    call_command("classer_produits", "--modele", str(out))
    rows = _read(out)
    assert (rows["creme"]["categorie_jodhur"], rows["creme"]["statut"], rows["creme"]["appliquer"]) == (
        "visage", "sûr", "oui")  # fmt: skip
    assert (rows["contour"]["categorie_jodhur"], rows["contour"]["statut"], rows["contour"]["appliquer"]) == (
        "yeux", "sûr", "oui")  # fmt: skip
    assert rows["sans-zone"]["categorie_jodhur"] == "" and rows["sans-zone"]["appliquer"] == "non"


@pytest.mark.django_db
def test_apercu_puis_application(setup, tmp_path):
    out = tmp_path / "liste.csv"
    call_command("classer_produits", "--modele", str(out))
    report = tmp_path / "a.md"
    args = ["--liste", str(out), "--rendre-visibles", "visage,yeux"]
    call_command("classer_produits", *args, "--report", str(report))
    visage = Category.objects.get(slug="visage")
    assert not visage.is_active and not ProductCategory.objects.filter(category=visage).exists()  # aperçu
    text = report.read_text(encoding="utf-8")
    assert "**Visage** (`visage`) : 1 produit(s) actif(s)" in text
    assert "**Visage › Yeux** (`yeux`) : 1 produit(s) actif(s)" in text and "reste masquée" not in text
    assert "aucune catégorie visible : **1**" in text and "`sans-zone`" in text  # pas de zone : à la main

    call_command("classer_produits", *args, "--appliquer")
    visage.refresh_from_db()
    assert visage.is_active and list(visage.products.all()) == [setup["a"]]
    yeux = Category.objects.get(slug="yeux")
    assert yeux.is_active and list(yeux.products.all()) == [setup["b"]]
    assert setup["a"].categories.filter(slug="eclat").exists()  # rien n'est retiré


@pytest.mark.django_db
def test_besoin_refuse_dans_rendre_visibles(setup):
    with pytest.raises(CommandError):
        call_command("classer_produits", "--rendre-visibles", "eclat", "--appliquer")
