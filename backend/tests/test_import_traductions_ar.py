"""Import des traductions arabes : aperçu sans écriture, contrôle du français, statut validé, rien d'autre touché."""

import json
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from apps.catalog.models import Product, ProductHighlight, Variant
from apps.orders.models import Order


def source(p):
    return {
        "display_name": p.display_name,
        "short_description": p.short_description,
        "summary": p.summary,
        "description_html": p.description_html,
        "ingredients": p.ingredients,
        "benefits": p.benefits,
        "usage_steps": p.usage_steps,
        "skin_types": p.skin_types,
        "highlights": [h.label for h in p.highlights.all()],
    }


@pytest.fixture
def gel(sellable):
    p = sellable(slug="gel-test", stock=7, price="99.00")
    Product.objects.filter(pk=p.pk).update(
        summary="Gel à l'aloe vera.",
        ingredients=["Aloe vera (indiqué sur l'emballage)"],
        usage_steps=["Appliquer.", "Faire pénétrer."],
    )
    p.highlights.all().delete()
    ProductHighlight.objects.create(product=p, icon="leaf", label="Aloe vera", position=0)
    p.refresh_from_db()
    return p


def write(tmp_path, gel, status="valide", **fields):
    row = {"slug": gel.slug, "content_status": status, "source_fr": source(gel), **fields}
    path = tmp_path / "trad.json"
    path.write_text(json.dumps({"format": "mpc-traductions-ar", "produits": [row]}, ensure_ascii=False), "utf-8")
    return str(path)


def run(*args):
    out = StringIO()
    call_command("import_traductions_ar", *args, stdout=out)
    return out.getvalue()


def commerce():
    return (
        list(Variant.objects.order_by("pk").values_list("price", "stock_quantity", "sku")),
        Order.objects.count(),
        list(Product.objects.order_by("pk").values_list("status", "slug")),
    )


FIELDS = dict(
    summary_ar="جل بالألوفيرا.",
    ingredients=["Aloe vera — mentionné sur l'emballage"],
    ingredients_ar=["الألوفيرا (Aloe vera) — مذكور على العبوة"],
    usage_steps_ar=["ضعوا الجل.", "ربّتوا بلطف."],
    highlights_ar=["ألوفيرا"],
    display_name_ar="",
)


@pytest.mark.django_db
def test_dry_run_affiche_les_changements_sans_ecrire(tmp_path, gel):
    before = Product.objects.values().get(pk=gel.pk)
    text = run(write(tmp_path, gel, **FIELDS), "--dry-run")
    assert "APERÇU" in text and "summary_ar" in text and "ingredients" in text and "picto 1" in text
    assert "display_name_ar" not in text  # vide = rien à écrire
    assert "Aucune donnée n'a été modifiée" in text
    assert Product.objects.values().get(pk=gel.pk) == before
    assert gel.highlights.get().label_ar == ""


@pytest.mark.django_db
def test_import_valide_ecrit_seulement_les_champs_prevus(tmp_path, gel):
    before = commerce()
    path = write(tmp_path, gel, **FIELDS)
    run(path)
    gel.refresh_from_db()
    assert gel.summary_ar == "جل بالألوفيرا." and gel.ingredients == ["Aloe vera — mentionné sur l'emballage"]
    assert gel.usage_steps == ["Appliquer.", "Faire pénétrer."]  # absent du fichier : inchangé
    assert gel.summary == "Gel à l'aloe vera." and gel.highlights.get().label_ar == "ألوفيرا"
    assert commerce() == before  # prix, stocks, statut, commandes intacts
    assert list(tmp_path.glob("trad.sauvegarde-*.json"))
    # 2e passage : le français optimisé est reconnu, rien d'inutile n'est réécrit.
    assert "aucun changement" in run(path)


@pytest.mark.django_db
def test_proposition_non_validee_jamais_ecrite(tmp_path, gel):
    text = run(write(tmp_path, gel, status="proposition", **FIELDS))
    gel.refresh_from_db()
    assert "non validé" in text and gel.summary_ar == ""


@pytest.mark.django_db
def test_francais_modifie_depuis_la_traduction_refuse(tmp_path, gel):
    path = write(tmp_path, gel, **FIELDS)
    Product.objects.filter(pk=gel.pk).update(summary="Texte modifié dans l'admin.")
    text = run(path)
    gel.refresh_from_db()
    assert "le français de la base a changé" in text and gel.summary_ar == ""


@pytest.mark.django_db
@pytest.mark.parametrize("extra,message", [({"price": 1}, "non autorisé"), ({"highlights_ar": ["a", "b"]}, "picto")])
def test_champs_interdits_ou_incoherents_refuses(tmp_path, gel, extra, message):
    text = run(write(tmp_path, gel, **{**FIELDS, **extra}))
    gel.refresh_from_db()
    assert message in text and gel.summary_ar == ""


@pytest.mark.django_db
def test_slug_inconnu_et_ligne_trop_longue(tmp_path, gel):
    path = tmp_path / "t.json"
    path.write_text(json.dumps({"format": "mpc-traductions-ar", "produits": [{"slug": "inconnu"}]}), "utf-8")
    assert "introuvable" in run(str(path), "--dry-run")
    with pytest.raises(CommandError):
        run(write(tmp_path, gel, short_description_ar="ا" * 161), "--dry-run")
