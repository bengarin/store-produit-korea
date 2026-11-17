"""
Les deux collections de la boutique, créées par `migrate` — SANS aucun produit : c'est l'équipe qui y range
les produits (Admin → Collections), une fois l'origine et les ingrédients vérifiés sur l'emballage.

- « Soins naturels » : n'accepte que des produits dont la liste d'ingrédients est renseignée.
- « Beauté chinoise » : n'accepte que des produits dont le pays de fabrication est la Chine.

Idempotent : une collection déjà présente (même slug) n'est ni dupliquée ni modifiée. Retour arrière : ne supprime rien.
"""

from django.db import migrations

# Textes figés ici (une migration ne doit pas dépendre du code applicatif). Modifiables ensuite dans l'admin.
COLLECTIONS = [
    {
        "slug": "soins-naturels",
        "name": "Soins naturels",
        "name_ar": "عناية طبيعية",
        "description": "Des soins qui mettent en avant des ingrédients d'origine végétale. "
        "La composition de chaque produit est détaillée sur sa fiche.",
        "description_ar": "منتجات عناية تُبرز مكوّنات من أصل نباتي. تجدون تركيبة كل منتج بالتفصيل في صفحته.",
        "position": 0,
        "require_ingredients": True,
        "required_origin": "",
    },
    {
        "slug": "beaute-chinoise",
        "name": "Beauté chinoise",
        "name_ar": "الجمال الصيني",
        "description": "Une sélection de soins fabriqués en Chine. "
        "Le pays de fabrication est indiqué sur chaque fiche.",
        "description_ar": "تشكيلة من منتجات العناية المصنوعة في الصين. بلد الصنع مذكور في صفحة كل منتج.",
        "position": 1,
        "require_ingredients": False,
        "required_origin": "CN",
    },
]


def create_collections(apps, schema_editor):
    Collection = apps.get_model("catalog", "Collection")
    for c in COLLECTIONS:
        data = dict(c)
        Collection.objects.get_or_create(slug=data.pop("slug"), defaults={**data, "is_active": True})


class Migration(migrations.Migration):
    dependencies = [("catalog", "0008_collections")]

    operations = [migrations.RunPython(create_collections, migrations.RunPython.noop)]
