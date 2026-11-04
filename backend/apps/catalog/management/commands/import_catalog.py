"""
Importe / met à jour le catalogue en UNE opération : backend/catalog_import/catalogue.json (français, photos,
visuels, catégories, pictos) + traductions/traductions_ar_6_produits.json (arabe, français optimisé des
ingrédients et du mode d'utilisation).

    python manage.py import_catalog --dry-run                    # aperçu : AUCUNE écriture
    python manage.py import_catalog --report rapport_import.md   # import réel + rapport

Règles :
- idempotent : produit retrouvé par son slug, image par son empreinte, lien image ↔ produit par (produit, média) ;
  une 2e exécution ne crée rien ;
- prix, prix barrés, stocks, autres variantes, statut (en ligne / brouillon) des produits EXISTANTS : jamais
  modifiés. Un produit NOUVEAU est créé en brouillon, variante à 0 DH (« prix à définir »), stock non renseigné ;
- traductions : seuls les produits dont « content_status » vaut « valide » sont importés, et seulement si le
  français traduit (« source_fr ») correspond encore au catalogue ; sinon l'arabe existant n'est ni écrit ni effacé ;
  une valeur vide n'efface jamais rien ;
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
TRANSLATIONS = Path(settings.BASE_DIR).parent / "traductions" / "traductions_ar_6_produits.json"
VALIDATED = "valide"
# Français optimisé fourni par le fichier de traductions (remplace la version du catalogue si validé).
FR_OVERRIDES = ["ingredients", "usage_steps"]
SOURCE_KEYS = [
    "display_name",
    "short_description",
    "summary",
    "description_html",
    "ingredients",
    "benefits",
    "usage_steps",
    "skin_types",
    "highlights",
]
LIST_FIELDS = {"ingredients", "benefits", "usage_steps", "ingredients_ar", "benefits_ar", "usage_steps_ar"}
MAX_LINES, MAX_LINE = 30, 500
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
    help = "Importe le catalogue complet (FR + traductions arabes validées). --dry-run : aperçu sans écriture."

    def add_arguments(self, parser):
        parser.add_argument("--manifest", default=str(IMPORT_ROOT / "catalogue.json"))
        parser.add_argument("--traductions", default=str(TRANSLATIONS), help="Fichier des traductions arabes.")
        parser.add_argument("--dry-run", action="store_true", help="Prévisualise sans rien écrire.")
        parser.add_argument("--report", help="Écrit le rapport Markdown dans ce fichier.")

    # ------------------------------------------------------------------ entrée
    def handle(self, *args, **options):
        self.dry = options["dry_run"]
        manifest = json.loads(Path(options["manifest"]).read_text(encoding="utf-8"))
        self.index = json.loads((IMPORT_ROOT / "images" / "INDEX.json").read_text(encoding="utf-8"))
        problems = self._validate(manifest)
        self.translations, self.categories_ar, self.tr_note = self._load_translations(
            Path(options["traductions"]), manifest, problems
        )
        if problems:
            raise CommandError("Fichier du catalogue invalide :\n- " + "\n- ".join(problems))

        self.new_media = {}  # empreinte → média (créé pendant cette exécution)
        reports = []
        try:
            with transaction.atomic():
                for p in manifest["products"]:
                    reports.append(self._product(p))
                self.category_changes = self._category_names()
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
                    errors.append(f"{s} : catégorie inconnue « {c} » (lancer `python manage.py migrate`).")
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

    # ----------------------------------------------------------- traductions
    def _load_translations(self, path: Path, manifest, errors):
        """Traductions par slug (contrôlées). Fichier absent = aucune traduction (signalé, pas une erreur)."""
        if not path.is_file():
            return {}, {}, f"Fichier de traductions absent ({path}) : arabe non importé."
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Traductions : JSON invalide ({exc}).")
            return {}, {}, ""
        if data.get("format") != "mpc-traductions-ar":
            errors.append("Traductions : format attendu « mpc-traductions-ar ».")
            return {}, {}, ""
        catalog = {p["slug"]: p for p in manifest.get("products", [])}
        rows, out = data.get("produits") or [], {}
        limits = {f.name: f.max_length for f in Product._meta.fields if getattr(f, "max_length", None)}
        for row in rows:
            slug = row.get("slug")
            if slug in out:
                errors.append(f"Traductions : produit « {slug} » en double.")
                continue
            if slug not in catalog:
                errors.append(f"Traductions : produit « {slug} » absent du catalogue.")
                continue
            out[slug] = row
            for key in [*AR_FIELDS, *FR_OVERRIDES]:
                value = row.get(key)
                if key in LIST_FIELDS:
                    if value is not None and (
                        not isinstance(value, list)
                        or len(value) > MAX_LINES
                        or any(not isinstance(x, str) or len(x) > MAX_LINE for x in value)
                    ):
                        errors.append(f"Traductions : {slug}.{key} : {MAX_LINES} lignes de {MAX_LINE} car. max.")
                elif value is not None and (not isinstance(value, str) or len(value) > limits.get(key, 20000)):
                    errors.append(f"Traductions : {slug}.{key} : texte trop long ou invalide.")
            labels = row.get("highlights_ar") or []
            if labels and (len(labels) != len(catalog[slug]["highlights"]) or any(len(x) > 60 for x in labels)):
                errors.append(f"Traductions : {slug}.highlights_ar : un libellé (60 car. max) par picto du catalogue.")
        missing = sorted(set(catalog) - set(out))
        note = f"Produits sans traduction : {', '.join(missing)}." if missing else ""
        return out, data.get("categories_ar") or {}, note

    def _translation(self, p: dict) -> tuple[dict | None, str]:
        """(traduction applicable ou None, état lisible)."""
        row = self.translations.get(p["slug"])
        if row is None:
            return None, "aucune traduction"
        status = row.get("content_status", "")
        if status != VALIDATED:
            return None, f"« {status or 'sans statut'} » : non importée (statut « {VALIDATED} » requis)"
        source = row.get("source_fr") or {}
        catalog = {k: p[k] for k in SOURCE_KEYS if k != "highlights"}
        catalog["highlights"] = [h["label"] for h in p["highlights"]]
        drift = [k for k in SOURCE_KEYS if source.get(k) != catalog[k]]
        if drift:
            return None, "CONFLIT : le français traduit ne correspond plus au catalogue (" + ", ".join(drift) + ")"
        return row, "validée : importée"

    @staticmethod
    def _clean(key, value):
        """Valeur à écrire, ou None si vide (une valeur vide n'efface jamais rien)."""
        if key in LIST_FIELDS:
            items = [x.strip() for x in (value or []) if x.strip()]
            return items or None
        text = (value or "").strip()
        if key.startswith("description_html"):
            text = sanitize_html(text)
        return text or None

    def _category_names(self) -> list[str]:
        """Noms arabes des catégories (bloc « categories_ar » du fichier), seulement si validés."""
        block = self.categories_ar
        if not block:
            return []
        if block.get("content_status") != VALIDATED:
            return [f"noms arabes des catégories : « {block.get('content_status', '')} », non importés"]
        changes = []
        for cat in Category.objects.filter(slug__in=[k for k, v in block.items() if isinstance(v, dict)]):
            new = (block[cat.slug].get("ar") or "").strip()[:100]
            if new and new != cat.name_ar:
                changes.append(f"catégorie {cat.slug} : name_ar « {cat.name_ar or '(vide)'} » → « {new} »")
                if not self.dry:
                    Category.objects.filter(pk=cat.pk).update(name_ar=new)
        return changes

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
            "fields": [],
        }
        tr, r["translation"] = self._translation(p)
        if r["translation"].startswith("CONFLIT"):
            r["warnings"].append("Traduction non importée : " + r["translation"])

        # Valeurs visées : français du catalogue (+ ingrédients / mode d'utilisation optimisés si traduction
        # validée), arabe seulement si traduction validée et non vide.
        target = {f: (sanitize_html(p[f]) if f == "description_html" else p[f]) for f in TEXT_FIELDS}
        if tr:
            for key in [*FR_OVERRIDES, *AR_FIELDS]:
                value = self._clean(key, tr.get(key))
                if value is not None:
                    target[key] = value
        for field, new in target.items():
            old = getattr(product, field) if product else ("" if field not in LIST_FIELDS else [])
            if product is None or old != new:
                if field != "position":
                    r["fields"].append((field, old, new))
                if product:
                    r["changes"].append(field)
                    setattr(product, field, new)
        if product is None:
            r["changes"].append("fiche créée (brouillon)")
        french_changed = any(f in TEXT_FIELDS for f in r["changes"])
        if product and not tr and french_changed and any(getattr(product, f) for f in AR_FIELDS):
            r["warnings"].append("Textes français modifiés : relire la traduction arabe existante (non modifiée).")

        # Statut : jamais modifié pour un produit existant ; un nouveau produit naît en brouillon.
        r["status"] = product.get_status_display() if product else "brouillon (nouveau)"
        if not self.dry:
            if product is None:
                product = Product(slug=slug, status=Product.Status.DRAFT, **target)
                product.save()
            elif r["changes"]:
                product.save()

        self._price(product, r)
        self._categories(product, p, r)
        self._highlights(product, p, r, (tr or {}).get("highlights_ar") or [])
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
            r["price"] = "à définir (0 DH)"
            return
        # Prix, prix barré et stock d'un produit existant : jamais modifiés par l'import.
        r["stock"] = "non renseigné" if variant.stock_quantity is None else f"{variant.stock_quantity} (inchangé)"
        r["price"] = "à définir (0 DH)" if variant.price == 0 else f"{variant.price} DH (inchangé)"
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

    def _highlights(self, product, p, r, labels_ar):
        wanted = p["highlights"]
        current = list(product.highlights.order_by("position")) if product and product.pk else []
        # Libellé arabe : celui de la traduction validée s'il est fourni, sinon l'existant (jamais effacé).
        ar = [
            (labels_ar[i].strip() if i < len(labels_ar) and labels_ar[i].strip() else None) for i in range(len(wanted))
        ]
        old = [(h.icon, h.label, h.label_ar) for h in current]
        new = [
            (h["icon"], h["label"], ar[i] if ar[i] is not None else (current[i].label_ar if i < len(current) else ""))
            for i, h in enumerate(wanted)
        ]
        if old[: len(new)] == new:
            return
        r["changes"].append("pictos")
        padded = (old + [None] * len(new))[: len(new)]
        for i, (o, n) in enumerate(zip(padded, new, strict=True)):
            if o != n:
                r["fields"].append((f"picto {i + 1}", " · ".join(o or ()) or "(absent)", " · ".join(n)))
        if (
            any(h.label_ar for h in current)
            and not labels_ar
            and [o[:2] for o in old[: len(new)]] != [n[:2] for n in new]
        ):
            r["warnings"].append("Pictos modifiés : leurs libellés arabes sont à revoir.")
        if self.dry:
            return
        for i, (icon, label, label_ar) in enumerate(new):
            row = current[i] if i < len(current) else ProductHighlight(product=product, position=i)
            row.icon, row.label, row.label_ar, row.position = icon, label, label_ar, i
            row.save()
        if len(current) > len(wanted):  # jamais supprimés : signalés
            r["warnings"].append(f"{len(current) - len(wanted)} picto(s) en plus non retiré(s).")

    def _gallery(self, product, p, r):
        rows = list(product.images.select_related("media")) if product and product.pk else []
        keep_ids = set()
        gallery_rows = []
        dirty = False
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
                dirty = True

        # Photo absente du fichier : MASQUÉE de la galerie (ligne et fichier conservés, aucune suppression).
        for old in rows:
            if old.pk in keep_ids or not old.in_gallery:
                continue
            r["removed_images"].append(f"{Path(old.media.file.name).name} masquée de la galerie (conservée)")
            if not self.dry:
                if product.hover_image_id == old.pk:
                    product.hover_image = None
                    dirty = True
                ProductImage.objects.filter(pk=old.pk).update(in_gallery=False)

        if not self.dry:
            hover = p.get("hover")
            hover_row = gallery_rows[hover["gallery_index"]] if hover else None
            position = (hover or {}).get("position", "")
            if product.hover_image_id != getattr(hover_row, "pk", None) or product.hover_image_position != position:
                product.hover_image, product.hover_image_position = hover_row, position
                dirty = True
            if dirty:  # enregistré seulement si quelque chose a changé
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
                r["marketing"].append(f"{label} — créé{' MASQUÉ' if m.get('active') is False else ''} (média {status})")
                if not self.dry:
                    # « active »: false = importé masqué (ex. traduction à corriger) ; ensuite, l'admin décide.
                    ProductMarketingImage.objects.create(
                        product=product, media=media, is_active=m.get("active", True), **attrs
                    )
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
        lines += [
            "| Produit | Action | Statut | Prix | Stock | Traduction arabe | Photos | Visuels |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in reports:
            lines.append(
                f"| {r['name']} | {r['action']} | {r['status']} | {r.get('price', '—')} | {r.get('stock', '—')} "
                f"| {r['translation']} | {len(r['images'])} | {len(r['marketing'])} |"
            )
        if self.tr_note:
            lines += ["", f"- {self.tr_note}"]
        lines += [f"- {x}" for x in getattr(self, "category_changes", [])]
        for r in reports:
            lines += ["", f"## {r['name']} (`{r['slug']}`) — {r['action']}"]
            if r["changes"]:
                lines.append("- Modifications : " + " ; ".join(r["changes"]))
            for field, old, new in r["fields"]:
                lines.append(f"- Champ `{field}` : {_short(old)} → {_short(new)}")
            lines += [f"- Image : {x}" for x in r["images"]]
            lines += [f"- Retrait : {x}" for x in r["removed_images"]]
            lines += [f"- Visuel : {x}" for x in r["marketing"]]
            lines += [f"- Visuel : {x}" for x in r["kept_marketing"]]
            lines += [f"- ⚠️ {x}" for x in r["warnings"]]
            lines += [f"- [DONNÉES MANQUANTES] {x}" for x in r["missing"]]
            lines += [f"- [À VÉRIFIER] {x}" for x in r["to_verify"]]
        return "\n".join(lines) + "\n"


def _short(value, size=110) -> str:
    text = " | ".join(value) if isinstance(value, list) else str(value if value not in (None, "") else "")
    text = text.replace("\n", " ")
    return "« " + ((text[: size - 1] + "…") if len(text) > size else text) + " »" if text else "(vide)"
