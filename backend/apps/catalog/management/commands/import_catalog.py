"""
Importe / met à jour les 6 produits de backend/catalog_import/catalogue.json dans MySQL.

    python manage.py import_catalog --dry-run                    # aperçu : AUCUNE écriture
    python manage.py import_catalog --report rapport_import.md   # import réel + rapport

Règles :
- idempotent : produit retrouvé par son slug, image par son empreinte, lien image ↔ produit par (produit, média) ;
  une 2e exécution ne crée rien ;
- prix NON renseignés : variante par défaut à 0 DH, prix barré retiré, produit en BROUILLON (le serveur refuse la
  mise en ligne tant que le prix vaut 0) ;
- stock jamais modifié ; champs arabes jamais écrits ni effacés ;
- aucune suppression : une photo absente du fichier est MASQUÉE de la galerie (ligne et fichier conservés),
  catégories et pictos en trop sont signalés, jamais retirés ;
- visuels marketing absents du fichier : laissés tels quels (signalés) ; aucun « Avant / Après » importé.
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.audit.services import log_action
from apps.catalog import services
from apps.catalog.models import (
    Category,
    Product,
    ProductCategory,
    ProductHighlight,
    ProductImage,
    ProductMarketingImage,
    Variant,
)
from apps.core.html import sanitize_html
from apps.media_library.models import MediaAsset
from apps.media_library.processing import inspect_existing

IMPORT_ROOT = Path(settings.BASE_DIR) / "catalog_import"
TEXT_FIELDS = [
    "position",
    "brand",
    "name",
    "display_name",
    "short_description",
    "summary",
    "description_html",
    "ingredients",
    "benefits",
    "usage_steps",
    "skin_types",
]
AR_FIELDS = [
    "display_name_ar",
    "short_description_ar",
    "summary_ar",
    "description_html_ar",
    "ingredients_ar",
    "benefits_ar",
    "usage_steps_ar",
    "skin_types_ar",
]


class DryRunRollback(Exception):
    pass


class Command(BaseCommand):
    help = "Importe les 6 produits du catalogue (prix laissés à définir). --dry-run : aperçu sans écriture."

    def add_arguments(self, parser):
        parser.add_argument("--manifest", default=str(IMPORT_ROOT / "catalogue.json"))
        parser.add_argument("--dry-run", action="store_true", help="Prévisualise sans rien écrire.")
        parser.add_argument("--report", help="Écrit le rapport Markdown dans ce fichier.")

    # ------------------------------------------------------------------ entrée
    def handle(self, *args, **options):
        self.dry = options["dry_run"]
        manifest = json.loads(Path(options["manifest"]).read_text(encoding="utf-8"))
        self.index = json.loads((IMPORT_ROOT / "images" / "INDEX.json").read_text(encoding="utf-8"))
        problems = self._validate(manifest)
        if problems:
            raise CommandError("Fichier du catalogue invalide :\n- " + "\n- ".join(problems))

        self.new_media = {}  # empreinte → média (créé pendant cette exécution)
        reports = []
        try:
            with transaction.atomic():
                for p in manifest["products"]:
                    reports.append(self._product(p))
                if self.dry:
                    raise DryRunRollback  # garantie supplémentaire : rien n'est conservé
                log_action(
                    "catalog.import",
                    changes={"products": [r["slug"] for r in reports], "source": "catalog_import/catalogue.json"},
                )
        except DryRunRollback:
            pass

        text = self._render(reports)
        if options.get("report"):
            Path(options["report"]).write_text(text, encoding="utf-8")
        self.stdout.write(text)

    # ------------------------------------------------------------ validation
    def _validate(self, manifest) -> list[str]:
        errors = []
        products = manifest.get("products", [])
        if len(products) != 6:
            errors.append(f"6 produits attendus, {len(products)} trouvés.")
        slugs = [p["slug"] for p in products]
        if len(set(slugs)) != len(slugs):
            errors.append("Slug en double.")
        known_categories = set(Category.objects.values_list("slug", flat=True))
        limits = {f.name: f.max_length for f in Product._meta.fields if getattr(f, "max_length", None)}
        icons = set(ProductHighlight.Icon.values)
        seen_files = set()
        for p in products:
            s = p["slug"]
            for field, value in p.items():
                if field in limits and isinstance(value, str) and len(value) > limits[field]:
                    errors.append(f"{s} : « {field} » dépasse {limits[field]} caractères.")
            if not p["gallery"]:
                errors.append(f"{s} : galerie vide.")
            for c in p["categories"]:
                if c not in known_categories:
                    errors.append(f"{s} : catégorie inconnue « {c} ».")
            for h in p["highlights"]:
                if h["icon"] not in icons or len(h["label"]) > 60:
                    errors.append(f"{s} : picto invalide « {h['label']} ».")
            for m in p["marketing"]:
                if m["category"] not in ProductMarketingImage.Category.values or m["category"] == "before_after":
                    errors.append(f"{s} : catégorie de visuel refusée « {m['category']} ».")
                if m["language"] not in ProductMarketingImage.Language.values:
                    errors.append(f"{s} : langue de visuel inconnue « {m['language']} ».")
            hover = p.get("hover")
            if hover and not 0 <= hover["gallery_index"] < len(p["gallery"]):
                errors.append(f"{s} : image de survol hors galerie.")
            entries = [*p["gallery"], *([p["scene"]] if p.get("scene") else []), *p["marketing"]]
            for e in entries:
                rel = e["file"]
                if not rel.startswith(f"images/{s}/"):
                    errors.append(f"{s} : image rangée chez un autre produit ({rel}).")
                if rel in seen_files:
                    errors.append(f"{s} : image utilisée deux fois ({rel}).")
                seen_files.add(rel)
                if rel not in self.index:
                    errors.append(f"{s} : {rel} absent de images/INDEX.json (lancer prepare_catalog_images).")
                    continue
                path = IMPORT_ROOT / rel
                if not path.is_file():
                    errors.append(f"{s} : fichier manquant {rel}.")
                    continue
                try:
                    inspect_existing(path.read_bytes())
                except Exception as exc:  # noqa: BLE001 - toute image illisible est signalée
                    errors.append(f"{s} : image illisible {rel} ({exc}).")
        return errors

    # --------------------------------------------------------------- médias
    def _media(self, entry: dict, alt: str, slug: str):
        """Retourne (média ou None en aperçu, 'réutilisé' | 'créé')."""
        info = self.index[entry["file"]]
        key = info["key_sha256"]
        media = MediaAsset.objects.filter(sha256=key).first() or self.new_media.get(key)
        if media:
            return media, "réutilisé"
        if self.dry:
            return None, "créé"
        main = (IMPORT_ROOT / entry["file"]).read_bytes()
        width, height, mime = inspect_existing(main)
        media = MediaAsset(
            original_filename=Path(info.get("original") or entry["file"]).name[:255],
            mime_type=mime,
            width=width,
            height=height,
            size_bytes=len(main),
            sha256=key,
            alt=alt[:255],
            source=MediaAsset.Source.IMPORT,
        )
        folder = f"catalogue/{slug}"
        media.file.save(f"{folder}/{Path(entry['file']).name}", ContentFile(main), save=False)
        if info.get("file_640"):
            small = (IMPORT_ROOT / info["file_640"]).read_bytes()
            media.file_640.save(f"{folder}/{Path(info['file_640']).name}", ContentFile(small), save=False)
        media.save()
        self.new_media[key] = media
        return media, "créé"

    # ------------------------------------------------------------- produits
    def _product(self, p: dict) -> dict:
        slug = p["slug"]
        product = Product.objects.filter(slug=slug).first()
        r = {
            "slug": slug,
            "name": p["display_name"],
            "action": "créé" if product is None else "mis à jour",
            "changes": [],
            "images": [],
            "removed_images": [],
            "marketing": [],
            "kept_marketing": [],
            "warnings": [],
            "format": p.get("format", ""),
            "missing": p.get("missing", []),
            "to_verify": p.get("to_verify", []),
        }

        # Champs texte (français)
        for field in TEXT_FIELDS:
            new = p[field]
            if field == "description_html":
                new = sanitize_html(new)
            if product and getattr(product, field) != new:
                r["changes"].append(field)
                setattr(product, field, new)
        if product is None:
            r["changes"].append("fiche créée")
        if product and any(getattr(product, f) for f in AR_FIELDS) and r["changes"]:
            r["warnings"].append("Textes français modifiés : relire la traduction arabe existante (non modifiée).")

        # Statut : brouillon tant que le prix n'est pas fixé
        old_status = product.status if product else None
        if product and old_status != Product.Status.DRAFT:
            r["changes"].append(f"statut {old_status or '—'} → brouillon")

        if not self.dry:
            if product is None:
                product = Product(slug=slug, status=Product.Status.DRAFT, **{f: p[f] for f in TEXT_FIELDS})
                product.description_html = sanitize_html(p["description_html"])
                product.save()
            else:
                product.status = Product.Status.DRAFT
                product.save()

        self._price(product, r)
        self._categories(product, p, r)
        self._highlights(product, p, r)
        self._gallery(product, p, r)
        self._marketing(product, p, r)
        if not r["changes"] and r["action"] == "mis à jour":
            r["action"] = "inchangé"
        return r

    def _price(self, product, r):
        variant = product.variants.filter(is_default=True).first() if product else None
        if variant is None:
            r["changes"].append("variante par défaut créée (prix à définir, stock non renseigné)")
            if not self.dry:
                Variant.objects.create(
                    product=product,
                    is_default=True,
                    title=services.DEFAULT_VARIANT_TITLE,
                    price=0,
                    stock_quantity=None,
                    track_inventory=True,
                )
            r["stock"] = "non renseigné"
            return
        r["stock"] = "non renseigné" if variant.stock_quantity is None else f"{variant.stock_quantity} (inchangé)"
        if variant.price != 0 or variant.compare_at_price is not None:
            r["changes"].append(f"prix {variant.price} DH (démo) → à définir")
            if not self.dry:
                Variant.objects.filter(pk=variant.pk).update(price=0, compare_at_price=None)
        others = product.variants.filter(is_default=False).count()
        if others:
            r["warnings"].append(f"{others} autre(s) variante(s) non modifiée(s) : vérifier leurs prix.")

    def _categories(self, product, p, r):
        wanted = p["categories"]
        current = (
            list(
                ProductCategory.objects.filter(product=product)
                .order_by("position")
                .values_list("category__slug", flat=True)
            )
            if product and product.pk
            else []
        )
        if current == wanted:
            return
        # Ajout seulement : un lien de catégorie en trop est signalé, jamais supprimé.
        missing = [s for s in wanted if s not in current]
        extra = [s for s in current if s not in wanted]
        if missing:
            r["changes"].append(f"catégories ajoutées {missing}")
        if extra:
            r["warnings"].append(f"Catégories en plus non retirées (à revoir dans l'administration) : {extra}")
        if missing and not self.dry:
            cats = {c.slug: c for c in Category.objects.filter(slug__in=missing)}
            start = len(current)
            ProductCategory.objects.bulk_create(
                [ProductCategory(product=product, category=cats[s], position=start + i) for i, s in enumerate(missing)]
            )

    def _highlights(self, product, p, r):
        wanted = p["highlights"]
        current = list(product.highlights.order_by("position")) if product and product.pk else []
        if [(h.icon, h.label) for h in current] == [(h["icon"], h["label"]) for h in wanted]:
            return
        r["changes"].append("pictos")
        if any(h.label_ar for h in current):
            r["warnings"].append("Pictos modifiés : leurs libellés arabes sont à revoir.")
        if self.dry:
            return
        for i, h in enumerate(wanted):
            row = current[i] if i < len(current) else ProductHighlight(product=product, position=i)
            if (row.icon, row.label) != (h["icon"], h["label"]):
                row.icon, row.label = h["icon"], h["label"]
            row.position = i
            row.save()
        if len(current) > len(wanted):  # jamais supprimés : signalés
            r["warnings"].append(f"{len(current) - len(wanted)} picto(s) en plus non retiré(s).")

    def _gallery(self, product, p, r):
        rows = list(product.images.select_related("media")) if product and product.pk else []
        keep_ids = set()
        gallery_rows = []
        wanted = [(e, True) for e in p["gallery"]] + ([(p["scene"], False)] if p.get("scene") else [])
        for position, (e, in_gallery) in enumerate(wanted):
            media, status = self._media(e, e["alt"], p["slug"])
            row = next((x for x in rows if media and x.media_id == media.pk and x.in_gallery == in_gallery), None)
            label = Path(e["file"]).name
            if row is None:
                r["images"].append(f"{label} — lien créé (média {status})")
                if not self.dry:
                    row = ProductImage.objects.create(
                        product=product,
                        media=media,
                        alt=e["alt"],
                        kind=e["kind"],
                        fit=e["fit"],
                        position=position,
                        in_gallery=in_gallery,
                    )
            else:
                attrs = {"alt": e["alt"], "kind": e["kind"], "fit": e["fit"], "position": position}
                if any(getattr(row, k) != v for k, v in attrs.items()):
                    r["images"].append(f"{label} — mis à jour (média réutilisé)")
                    if not self.dry:
                        ProductImage.objects.filter(pk=row.pk).update(**attrs)
                else:
                    r["images"].append(f"{label} — inchangé")
            if row is not None:
                keep_ids.add(row.pk)
            if in_gallery:
                gallery_rows.append(row)
            elif not self.dry and product.scene_image_id != row.pk:
                product.scene_image = row

        # Photo absente du fichier : MASQUÉE de la galerie (ligne et fichier conservés, aucune suppression).
        for old in rows:
            if old.pk in keep_ids or not old.in_gallery:
                continue
            r["removed_images"].append(f"{Path(old.media.file.name).name} masquée de la galerie (conservée)")
            if not self.dry:
                if product.hover_image_id == old.pk:
                    product.hover_image = None
                ProductImage.objects.filter(pk=old.pk).update(in_gallery=False)

        if not self.dry:
            hover = p.get("hover")
            product.hover_image = gallery_rows[hover["gallery_index"]] if hover else None
            product.hover_image_position = (hover or {}).get("position", "")
            product.save()

    def _marketing(self, product, p, r):
        rows = list(product.marketing_images.all()) if product and product.pk else []
        keep = set()
        for position, m in enumerate(p["marketing"]):
            media, status = self._media(m, m["alt"], p["slug"])
            row = next((x for x in rows if media and x.media_id == media.pk), None)
            label = Path(m["file"]).name
            attrs = {"category": m["category"], "language": m["language"], "alt": m["alt"], "position": position}
            if row is None:
                r["marketing"].append(f"{label} — créé (média {status})")
                if not self.dry:
                    ProductMarketingImage.objects.create(product=product, media=media, is_active=True, **attrs)
            else:
                keep.add(row.pk)
                if any(getattr(row, k) != v for k, v in attrs.items()):
                    r["marketing"].append(f"{label} — mis à jour (média réutilisé)")
                    if not self.dry:
                        ProductMarketingImage.objects.filter(pk=row.pk).update(**attrs)
                else:
                    r["marketing"].append(f"{label} — inchangé")
        for row in rows:
            if row.pk not in keep:
                r["kept_marketing"].append(f"visuel n° {row.pk} ({row.category}) non listé : laissé tel quel")

    # --------------------------------------------------------------- rapport
    def _render(self, reports) -> str:
        mode = "APERÇU (--dry-run) : rien n'a été écrit" if self.dry else "IMPORT RÉEL"
        lines = [f"# Import du catalogue — {mode}", ""]
        lines += ["| Produit | Action | Format | Prix | Stock | Photos | Visuels |", "|---|---|---|---|---|---|---|"]
        for r in reports:
            lines.append(
                f"| {r['name']} | {r['action']} | {r['format']} | À définir | {r.get('stock', '—')} "
                f"| {len(r['images'])} | {len(r['marketing'])} |"
            )
        for r in reports:
            lines += ["", f"## {r['name']} (`{r['slug']}`) — {r['action']}"]
            if r["changes"]:
                lines.append("- Modifications : " + " ; ".join(r["changes"]))
            lines += [f"- Image : {x}" for x in r["images"]]
            lines += [f"- Retrait : {x}" for x in r["removed_images"]]
            lines += [f"- Visuel : {x}" for x in r["marketing"]]
            lines += [f"- Visuel : {x}" for x in r["kept_marketing"]]
            lines += [f"- ⚠️ {x}" for x in r["warnings"]]
            lines += [f"- [DONNÉES MANQUANTES] {x}" for x in r["missing"]]
            lines += [f"- [À VÉRIFIER] {x}" for x in r["to_verify"]]
        return "\n".join(lines) + "\n"
