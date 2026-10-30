"""
Importe le catalogue de démonstration du front (5 produits, 3 catégories, images) dans MySQL.

    python manage.py import_demo_catalog            # crée ce qui manque, ne touche PAS aux produits existants
    python manage.py import_demo_catalog --update   # ré-aligne aussi les produits existants sur le fichier

Source : apps/catalog/fixtures/demo_catalog.json, généré depuis le front par
`node scripts/export-demo-catalog.mjs` (aucune donnée recopiée à la main).
Les images sont copiées à l'identique depuis src/assets (rendu inchangé).
"""

import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_action
from apps.catalog import services
from apps.catalog.models import Category, Product, ProductCategory, ProductHighlight, ProductImage, Variant
from apps.media_library.services import create_from_repository_file

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "demo_catalog.json"
REPO_ROOT = Path(settings.BASE_DIR).parent
ASSETS_ROOT = (REPO_ROOT / "src" / "assets").resolve()


def repo_file(relative: str | None) -> Path | None:
    if not relative:
        return None
    path = (REPO_ROOT / relative).resolve()
    if ASSETS_ROOT not in path.parents:  # n'importe que des fichiers de src/assets
        raise CommandError(f"Chemin refusé : {relative}")
    if not path.is_file():
        raise CommandError(f"Image introuvable : {relative}")
    return path


class Command(BaseCommand):
    help = "Importe les 5 produits de démonstration du front dans MySQL."

    def add_arguments(self, parser):
        parser.add_argument("--update", action="store_true", help="Met aussi à jour les produits déjà présents.")

    @transaction.atomic
    def handle(self, *args, **options):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        categories = {}
        for c in data["categories"]:
            category, _ = Category.objects.update_or_create(
                slug=c["slug"], defaults={"name": c["name"], "position": c["position"], "is_active": True}
            )
            categories[c["slug"]] = category

        created, updated, skipped = [], [], []
        for p in data["products"]:
            product = Product.objects.filter(slug=p["slug"]).first()
            if product and not options["update"]:
                skipped.append(p["slug"])
                continue
            (created if product is None else updated).append(p["slug"])
            self._import_product(product, p, categories)

        log_action("catalog.import", changes={"created": created, "updated": updated, "skipped": skipped})
        self.stdout.write(
            self.style.SUCCESS(
                f"Catégories : {len(categories)} · produits créés : {len(created)}, mis à jour : {len(updated)}, "
                f"inchangés : {len(skipped)}"
            )
        )

    def _import_product(self, product, p, categories):
        fields = {
            "position": p["position"],
            "brand": p["brand"],
            "name": p["name"],
            "display_name": p["displayName"],
            "short_description": p["cardLine"],
            "summary": p["summary"],
            "ingredients": p["ingredients"],
            "benefits": p["benefits"],
            "usage_steps": p["usage"],
            "skin_types": p["skinTypes"],
        }
        if product is None:
            product = Product.objects.create(slug=p["slug"], **fields)
        else:
            Product.objects.filter(pk=product.pk).update(hover_image=None, scene_image=None, **fields)
            product.refresh_from_db()

        ProductCategory.objects.filter(product=product).delete()
        ProductCategory.objects.bulk_create(
            [
                ProductCategory(product=product, category=categories[slug], position=i)
                for i, slug in enumerate(p["categories"])
            ]
        )
        product.highlights.all().delete()
        ProductHighlight.objects.bulk_create(
            [
                ProductHighlight(product=product, icon=h["icon"], label=h["label"], position=i)
                for i, h in enumerate(p["highlights"])
            ]
        )

        product.images.all().delete()  # les médias restent (dédoublonnés par empreinte)
        folder = f"imports/{p['slug']}"
        gallery = []
        for i, img in enumerate(p["gallery"]):
            media = create_from_repository_file(
                repo_file(img["file"]), alt=img["alt"], path_640=repo_file(img["file640"]), folder=folder
            )
            gallery.append(
                ProductImage.objects.create(
                    product=product,
                    media=media,
                    alt=img["alt"],
                    kind=img["kind"],
                    fit=img["fit"],
                    position=i,
                )
            )
        scene = None
        if p["scene"]:
            s = p["scene"]
            media = create_from_repository_file(
                repo_file(s["file"]), alt=s["alt"], path_640=repo_file(s["file640"]), folder=folder
            )
            scene = ProductImage.objects.create(
                product=product,
                media=media,
                alt=s["alt"],
                kind=s["kind"],
                fit=s["fit"],
                position=len(gallery),
                in_gallery=False,
            )
        hover = p["hover"]
        product.scene_image = scene
        product.hover_image = gallery[hover["galleryIndex"]] if hover else None
        product.hover_image_position = (hover or {}).get("position", "")

        # Variante par défaut. Stock réel inconnu [DONNÉES MANQUANTES] : suivi désactivé en attendant.
        variant = product.variants.filter(is_default=True).first() or Variant(product=product, is_default=True)
        variant.title = services.DEFAULT_VARIANT_TITLE
        variant.price = Decimal(str(p["price"]))
        variant.track_inventory = False
        variant.save()

        errors = services.activation_errors(product)
        if errors:
            raise CommandError(f"{p['slug']} : {' '.join(errors)}")
        product.status = Product.Status.ACTIVE
        product.published_at = product.published_at or timezone.now()
        product.save()
