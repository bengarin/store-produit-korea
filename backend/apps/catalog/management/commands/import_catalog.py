"""
Met à jour les TEXTES des 6 produits en UNE opération : backend/catalog_import/catalogue.json (français d'origine,
catégories, pictos) + traductions/traductions_ar_6_produits.json (nouveaux textes FR, textes AR, pictos FR/AR).

    python manage.py import_catalog --dry-run --simuler-valide   # aperçu : AUCUNE écriture
    python manage.py import_catalog --report rapport_import.md   # import réel + rapport

Règles :
- seuls les produits dont « content_status » vaut « valide » sont importés ;
- un texte FR n'est remplacé que s'il est encore l'original (« source_fr ») ; un texte modifié dans l'admin est
  conservé et signalé « CONFLIT » ; un texte AR n'est écrit que si son français correspond ; une valeur vide
  n'efface jamais rien ;
- idempotent : produit retrouvé par son slug, pictos par leur position ; une 2e exécution n'écrit rien ;
- prix, prix barrés, stocks, variantes, statut, catégories des produits EXISTANTS : jamais modifiés. Un produit
  NOUVEAU est créé en brouillon, variante à 0 DH (« prix à définir »), stock non renseigné ;
- IMAGES : jamais touchées. Aucune photo ni aucun visuel n'est ajouté, modifié, masqué ou réordonné, même s'il
  manque en base (le rapport les liste seulement) : les images se gèrent à la main dans l'admin ;
- aucune suppression : catégories et pictos en trop sont signalés, jamais retirés.
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.audit.services import log_action
from apps.catalog import services
from apps.catalog.models import (
    Category,
    Product,
    ProductCategory,
    ProductHighlight,
    ProductMarketingImage,
    Variant,
)
from apps.core.html import sanitize_html
from apps.media_library.processing import inspect_existing

IMPORT_ROOT = Path(settings.BASE_DIR) / "catalog_import"
TRANSLATIONS = Path(settings.BASE_DIR).parent / "traductions" / "traductions_ar_6_produits.json"
VALIDATED = "valide"
# Nouveaux textes français (marketing) fournis par le fichier de contenu : ils remplacent le texte en base
# seulement si celui-ci est encore l'original traduit (« source_fr ») — un texte modifié dans l'admin est conservé.
FR_OVERRIDES = [
    "short_description",
    "summary",
    "description_html",
    "benefits",
    "ingredients",
    "usage_steps",
    "skin_types",
]
LIST_FIELDS = {"ingredients", "benefits", "usage_steps", "ingredients_ar", "benefits_ar", "usage_steps_ar"}
MAX_LINES, MAX_LINE = 30, 500
# (champ français, champ arabe) : chaque traduction dépend du texte français de la même ligne.
PAIRS = [
    ("display_name", "display_name_ar"),
    ("short_description", "short_description_ar"),
    ("summary", "summary_ar"),
    ("description_html", "description_html_ar"),
    ("ingredients", "ingredients_ar"),
    ("benefits", "benefits_ar"),
    ("usage_steps", "usage_steps_ar"),
    ("skin_types", "skin_types_ar"),
]
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
    help = "Met à jour les textes FR/AR et pictos des 6 produits (jamais les images). --dry-run : aperçu sans écriture."

    def add_arguments(self, parser):
        parser.add_argument("--manifest", default=str(IMPORT_ROOT / "catalogue.json"))
        parser.add_argument("--traductions", default=str(TRANSLATIONS), help="Fichier des traductions arabes.")
        parser.add_argument("--dry-run", action="store_true", help="Prévisualise sans rien écrire.")
        parser.add_argument("--report", help="Écrit le rapport Markdown dans ce fichier.")
        parser.add_argument(
            "--simuler-valide",
            action="store_true",
            help="Avec --dry-run seulement : montre ce qui serait importé si les traductions étaient « valide ».",
        )

    # ------------------------------------------------------------------ entrée
    def handle(self, *args, **options):
        self.dry = options["dry_run"]
        self.simulate = options["simuler_valide"]
        if self.simulate and not self.dry:
            raise CommandError("--simuler-valide n'est autorisé qu'avec --dry-run (aucune écriture).")
        manifest = json.loads(Path(options["manifest"]).read_text(encoding="utf-8"))
        self.index = json.loads((IMPORT_ROOT / "images" / "INDEX.json").read_text(encoding="utf-8"))
        problems = self._validate(manifest)
        self.translations, self.categories_ar, self.tr_note = self._load_translations(
            Path(options["traductions"]), manifest, problems
        )
        if problems:
            raise CommandError("Fichier du catalogue invalide :\n- " + "\n- ".join(problems))

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
            for key in ("highlights", "highlights_ar"):
                labels = row.get(key) or []
                if labels and (
                    len(labels) != len(catalog[slug]["highlights"])
                    or any(not isinstance(x, str) or len(x) > 60 for x in labels)
                ):
                    errors.append(f"Traductions : {slug}.{key} : un libellé (60 car. max) par picto du catalogue.")
        missing = sorted(set(catalog) - set(out))
        note = f"Produits sans traduction : {', '.join(missing)}." if missing else ""
        return out, data.get("categories_ar") or {}, note

    def _translation(self, p: dict) -> tuple[dict | None, str]:
        """(traduction applicable ou None, état lisible). La correspondance du français est vérifiée champ par champ."""
        row = self.translations.get(p["slug"])
        if row is None:
            return None, "aucune traduction"
        status = row.get("content_status", "")
        if status == VALIDATED:
            return row, "validée"
        if self.simulate:
            return row, f"« {status or 'sans statut'} » — SIMULATION « {VALIDATED} » (aperçu seulement)"
        return None, f"« {status or 'sans statut'} » : non importée (statut « {VALIDATED} » requis)"

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
        status = block.get("content_status", "")
        if status != VALIDATED and not self.simulate:
            return [f"Noms arabes des catégories : « {status} », non importés (statut « {VALIDATED} » requis)"]
        prefix = "SIMULATION — " if status != VALIDATED else ""
        changes = []
        for cat in Category.objects.filter(slug__in=[k for k, v in block.items() if isinstance(v, dict)]):
            new = (block[cat.slug].get("ar") or "").strip()[:100]
            if new and new != cat.name_ar:
                changes.append(f"{prefix}catégorie {cat.slug} : name_ar « {cat.name_ar or '(vide)'} » → « {new} »")
                if not self.dry and not prefix:
                    Category.objects.filter(pk=cat.pk).update(name_ar=new)
        return changes

    # ------------------------------------------------------------- produits
    def _product(self, p: dict) -> dict:
        slug = p["slug"]
        product = Product.objects.filter(slug=slug).first()
        self.is_new = product is None  # fixé avant toute écriture (le produit nouveau est créé plus bas)
        r = {
            "slug": slug,
            "name": p["display_name"],
            "action": "créé" if product is None else "mis à jour",
            "changes": [],
            "images": [],
            "missing_images": [],
            "warnings": [],
            "format": p.get("format", ""),
            "missing": p.get("missing", []),
            "to_verify": p.get("to_verify", []),
            "rows": [],  # (champ, français actuel, proposition, résultat) pour le rapport
            "kept_fr": [],  # français du catalogue différent de la base : conservé (jamais réécrit)
        }
        tr, r["translation"] = self._translation(p)
        source = (tr or {}).get("source_fr") or {}

        # Français : un produit EXISTANT garde ses textes (modifiés dans l'admin ou non) ; le catalogue ne sert
        # qu'à créer un produit nouveau.
        catalog_fr = {f: (sanitize_html(p[f]) if f == "description_html" else p[f]) for f in TEXT_FIELDS}
        base = dict(catalog_fr) if product is None else {f: getattr(product, f) for f in TEXT_FIELDS}
        writes = {}

        def decide(fr_field, key, label):
            """Une ligne du rapport : écrit la proposition si elle est applicable, sinon dit pourquoi."""
            proposal = self._clean(key, (self.translations.get(slug) or {}).get(key))
            current = base[key] if key in base else (getattr(product, key) if product else "")
            if proposal is None:
                result = "rien à importer (aucune proposition)"
            elif tr is None:
                result = "non importé : " + r["translation"]
            elif base[fr_field] != source.get(fr_field) and not (
                fr_field in FR_OVERRIDES and base[fr_field] == self._clean(fr_field, tr.get(fr_field))
            ):
                result = "CONFLIT : français différent de celui traduit — rien n'est écrit"
                r["warnings"].append(
                    f"{label} : le français actuel ne correspond pas au texte traduit (« source_fr »)."
                )
            elif proposal == current:
                result = "inchangé (déjà identique)"
            else:
                result = "IMPORTÉ"
                writes[key] = proposal
            r["rows"].append((label, base[fr_field], proposal, result))

        for fr_field, ar_field in PAIRS:
            if fr_field in FR_OVERRIDES:
                decide(fr_field, fr_field, f"{fr_field} (FR)")
            decide(fr_field, ar_field, ar_field)

        if product is not None:
            # Français de la base différent de catalogue.json et non remplacé : conservé tel quel (signalé).
            r["kept_fr"] = [f for f in TEXT_FIELDS if f != "position" and base[f] != catalog_fr[f] and f not in writes]
        for key, value in writes.items():
            r["changes"].append(key)
            if product is not None:
                setattr(product, key, value)
        if product is None:
            r["changes"].append("fiche créée (brouillon)")

        # Statut : jamais modifié pour un produit existant ; un nouveau produit naît en brouillon.
        r["status"] = product.get_status_display() if product else "brouillon (nouveau)"
        if not self.dry:
            if product is None:
                product = Product(slug=slug, status=Product.Status.DRAFT, **{**base, **writes})
                product.save()
            elif writes:
                product.save(update_fields=[*writes, "updated_at"])

        self._price(product, r)
        self._categories(product, p, r)
        self._highlights(product, p, r, tr, source)
        self._images(product, p, r)
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
        if not self.is_new:
            # Produit existant : catégories gérées dans l'admin, jamais modifiées (différences signalées).
            current = list(
                ProductCategory.objects.filter(product=product)
                .order_by("position")
                .values_list("category__slug", flat=True)
            )
            if set(current) != set(wanted):
                r["warnings"].append(f"Catégories : base {current}, catalogue {wanted} — base conservée.")
            return
        r["changes"].append(f"catégories {wanted}")
        if not self.dry:
            cats = {c.slug: c for c in Category.objects.filter(slug__in=wanted)}
            ProductCategory.objects.bulk_create(
                [ProductCategory(product=product, category=cats[s], position=i) for i, s in enumerate(wanted)]
            )

    def _highlights(self, product, p, r, tr, source):
        """
        Pictos (icône, libellé FR, libellé AR), par position. Icônes jamais modifiées.
        Libellé FR : remplacé par le nouveau texte du fichier de contenu seulement s'il est encore l'original
        (« source_fr ») ; libellé AR : écrit si le libellé FR est l'original ou le nouveau texte. Rien n'est supprimé.
        """
        existing = not self.is_new
        current = list(product.highlights.order_by("position")) if existing else []
        if not existing:
            r["changes"].append("pictos créés")
        row = self.translations.get(p["slug"]) or {}
        new_fr_all, new_ar_all = row.get("highlights") or [], row.get("highlights_ar") or []
        sources = source.get("highlights") or []
        labels = [h.label for h in current] if existing else [h["label"] for h in p["highlights"]]
        pick = lambda xs, i: (xs[i].strip() or None) if i < len(xs) else None  # noqa: E731
        new_fr, new_ar = {}, {}
        for i, fr in enumerate(labels):
            original = sources[i] if i < len(sources) else None
            proposal_fr, proposal_ar = pick(new_fr_all, i), pick(new_ar_all, i)
            fr_ok = fr == original or (proposal_fr is not None and fr == proposal_fr)
            for kind, proposal, current_value, out in (
                ("label FR", proposal_fr, fr, new_fr),
                ("label_ar", proposal_ar, current[i].label_ar if existing else "", new_ar),
            ):
                if proposal is None:
                    result = "rien à importer (aucune proposition)"
                elif tr is None:
                    result = "non importé : " + r["translation"]
                elif not fr_ok:
                    result = "CONFLIT : picto français modifié depuis la traduction — rien n'est écrit"
                    r["warnings"].append(f"picto {i + 1} : le libellé français ne correspond pas au texte traduit.")
                elif proposal == current_value:
                    result = "inchangé (déjà identique)"
                else:
                    result = "IMPORTÉ"
                    out[i] = proposal
                r["rows"].append((f"picto {i + 1} ({kind})", fr, proposal, result))
        if new_fr:
            r["changes"].append("pictos (FR)")
        if new_ar:
            r["changes"].append("pictos (AR)")
        if existing and [new_fr.get(i, x) for i, x in enumerate(labels)] != [h["label"] for h in p["highlights"]]:
            r["kept_fr"].append("pictos")
        if self.dry:
            return
        if not existing:
            for i, h in enumerate(p["highlights"]):
                ProductHighlight.objects.create(
                    product=product,
                    position=i,
                    icon=h["icon"],
                    label=new_fr.get(i, h["label"]),
                    label_ar=new_ar.get(i, ""),
                )
            return
        for i in set(new_fr) | set(new_ar):
            fields = {}
            if i in new_fr:
                fields["label"] = new_fr[i]
            if i in new_ar:
                fields["label_ar"] = new_ar[i]
            ProductHighlight.objects.filter(pk=current[i].pk).update(**fields)

    def _images(self, product, p, r):
        """Photos et visuels : LECTURE SEULE. Rien n'est ajouté, modifié, masqué ni réordonné, même si une image
        du catalogue manque en base : les images sont gérées à la main dans l'admin. Le rapport dit seulement
        ce qui est en base et ce qui manque."""
        photos = list(product.images.select_related("media")) if not self.is_new else []
        visuals = list(product.marketing_images.select_related("media")) if not self.is_new else []
        have = {x.media.sha256 for x in photos} | {x.media.sha256 for x in visuals}
        r["images"].append(
            f"en base : {sum(1 for x in photos if x.in_gallery)} photo(s) en galerie, {len(visuals)} visuel(s) "
            "— conservés tels quels (l'import ne touche jamais aux images)"
        )
        wanted = [*p["gallery"], *([p["scene"]] if p.get("scene") else []), *p["marketing"]]
        for e in wanted:
            if self.index[e["file"]]["key_sha256"] not in have:
                r["missing_images"].append(Path(e["file"]).name)

    # --------------------------------------------------------------- rapport
    def _render(self, reports) -> str:
        mode = "APERÇU (--dry-run) : rien n'a été écrit" if self.dry else "IMPORT RÉEL"
        if self.simulate:
            mode += " — SIMULATION : les traductions « proposition » sont traitées comme « valide »"
        lines = [f"# Import du catalogue — {mode}", ""]
        lines += [
            "Règle : un produit existant garde son prix, son stock, ses variantes, son statut et ses catégories.",
            "Les images (photos et visuels) ne sont jamais ajoutées, modifiées, masquées ni réordonnées.",
            "Les nouveaux textes FR et AR du fichier de contenu (produits « valide ») remplacent un texte seulement",
            "s'il est encore l'original ; un texte modifié dans l'admin est conservé (CONFLIT signalé).",
            "",
            "| Produit | Action | Statut | Prix | Stock | Traduction arabe | Champs importés | Conflits |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in reports:
            imported = sum(1 for row in r["rows"] if row[3] == "IMPORTÉ")
            conflicts = sum(1 for row in r["rows"] if row[3].startswith("CONFLIT"))
            lines.append(
                f"| {r['name']} | {r['action']} | {r['status']} | {r.get('price', '—')} | {r.get('stock', '—')} "
                f"| {r['translation']} | {imported} | {conflicts} |"
            )
        if self.tr_note:
            lines += ["", f"- {self.tr_note}"]
        lines += [f"- {x}" for x in getattr(self, "category_changes", [])]
        for r in reports:
            lines += ["", f"## {r['name']} (`{r['slug']}`) — {r['action']}", ""]
            lines += [f"- Traduction : {r['translation']}"]
            if r["changes"]:
                lines.append("- Écritures prévues : " + " ; ".join(r["changes"]))
            if r["kept_fr"]:
                lines.append("- Français conservé (base ≠ catalogue.json, jamais réécrit) : " + ", ".join(r["kept_fr"]))
            lines += ["", "| Champ | Français actuel | Proposition | Résultat |", "|---|---|---|---|"]
            lines += [f"| {f} | {_cell(fr)} | {_cell(prop)} | {res} |" for f, fr, prop, res in r["rows"]]
            lines.append("")
            lines += [f"- Images : {x}" for x in r["images"]]
            if r["missing_images"]:
                lines.append(
                    f"- Images du catalogue absentes de la base (NON ajoutées, à gérer dans l'admin) : "
                    f"{len(r['missing_images'])} — " + ", ".join(r["missing_images"])
                )
            lines += [f"- ⚠️ {x}" for x in r["warnings"]]
            lines += [f"- [DONNÉES MANQUANTES] {x}" for x in r["missing"]]
            lines += [f"- [À VÉRIFIER] {x}" for x in r["to_verify"]]
        return "\n".join(lines) + "\n"


def _cell(value, size=80) -> str:
    """Valeur courte pour une cellule de tableau Markdown."""
    if value is None or value == "" or value == []:
        return "(vide)"
    text = " / ".join(value) if isinstance(value, list) else str(value)
    text = text.replace("\n", " ").replace("|", "\\|")
    return (text[: size - 1] + "…") if len(text) > size else text
