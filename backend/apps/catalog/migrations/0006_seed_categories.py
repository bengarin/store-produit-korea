"""
Catégories de base du catalogue, créées automatiquement par `migrate` (base neuve comprise).

Les slugs sont ceux de backend/catalog_import/catalogue.json : `import_catalog` les exige.
Idempotent : une catégorie déjà présente (même slug) n'est ni dupliquée ni modifiée (nom, ordre, visibilité
et traduction arabe saisis dans l'administration sont conservés). Retour arrière : ne supprime rien.
"""

from django.db import migrations

# Liste figée ici (une migration ne doit pas dépendre du code applicatif, qui peut changer).
CATEGORIES = [
    {"slug": "hydratation", "name": "Hydratation", "position": 0},
    {"slug": "anti-age", "name": "Anti-âge", "position": 1},
    {"slug": "eclat", "name": "Éclat", "position": 2},
]


def create_categories(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    for c in CATEGORIES:
        Category.objects.get_or_create(
            slug=c["slug"], defaults={"name": c["name"], "position": c["position"], "is_active": True}
        )


class Migration(migrations.Migration):
    dependencies = [("catalog", "0005_marketing_images")]

    operations = [migrations.RunPython(create_categories, migrations.RunPython.noop)]
