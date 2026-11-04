"""
Import des traductions arabes (et des ingrédients / consignes optimisés en français) des fiches produits,
depuis traductions/traductions_ar_6_produits.json.

    python manage.py import_traductions_ar ../traductions/traductions_ar_6_produits.json --dry-run
    python manage.py import_traductions_ar ../traductions/traductions_ar_6_produits.json

Sécurité :
- seuls les champs de contenu listés dans FIELDS peuvent être écrits (jamais prix, stocks, variantes, statut,
  commandes, catégories, images) ; aucun champ ni aucune structure n'est ajouté ;
- chaque produit est retrouvé par son slug ; le français actuel de la base doit correspondre à `source_fr`
  (sinon le produit est refusé : la traduction ne correspond plus au texte) ;
- valeur vide = rien n'est écrit ; valeur identique à la base = rien n'est écrit ;
- sans --dry-run : seuls les produits « content_status": "valide" » sont écrits, après une sauvegarde JSON des
  anciennes valeurs, dans une seule transaction (tout ou rien).
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_action
from apps.catalog.models import Product
from apps.core.html import sanitize_html

TEXT, LINES, HTML = "text", "lines", "html"
# Champ du fichier → (type, longueur max, champ français dont dépend la traduction)
FIELDS = {
    "display_name_ar": (TEXT, 255, "display_name"),
    "short_description_ar": (TEXT, 160, "short_description"),
    "summary_ar": (TEXT, 5000, "summary"),
    "description_html_ar": (HTML, 20000, "description_html"),
    "ingredients": (LINES, 500, "ingredients"),
    "ingredients_ar": (LINES, 500, "ingredients"),
    "benefits_ar": (LINES, 500, "benefits"),
    "usage_steps": (LINES, 500, "usage_steps"),
    "usage_steps_ar": (LINES, 500, "usage_steps"),
    "skin_types_ar": (TEXT, 255, "skin_types"),
}
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
VALIDATED = "valide"


def short(value, size=90):
    text = " | ".join(value) if isinstance(value, list) else str(value or "")
    return (text[: size - 1] + "…") if len(text) > size else (text or "(vide)")


def clean(key, value, where):
    """Valeur prête à écrire, ou None si vide (= ne rien écrire)."""
    kind, max_length, _ = FIELDS[key]
    if kind == LINES:
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            raise CommandError(f"{where} : liste de textes attendue.")
        items = [x.strip() for x in value if x.strip()]
        if any(len(x) > max_length for x in items) or len(items) > 30:
            raise CommandError(f"{where} : 30 lignes de {max_length} caractères au maximum.")
        if len(set(items)) != len(items):
            raise CommandError(f"{where} : ligne en double.")
        return items or None
    if not isinstance(value, str):
        raise CommandError(f"{where} : texte attendu.")
    text = value.strip()
    if len(text) > max_length:
        raise CommandError(f"{where} : {len(text)} caractères (maximum {max_length}).")
    return (sanitize_html(text) if kind == HTML else text) or None


def current_source(product):
    return {
        "display_name": product.display_name,
        "short_description": product.short_description,
        "summary": product.summary,
        "description_html": product.description_html,
        "ingredients": product.ingredients,
        "benefits": product.benefits,
        "usage_steps": product.usage_steps,
        "skin_types": product.skin_types,
        "highlights": [h.label for h in product.highlights.all()],
    }


class Command(BaseCommand):
    help = "Importe les traductions arabes validées (et le français optimisé des ingrédients / consignes)."

    def add_arguments(self, parser):
        parser.add_argument("file", help="Fichier JSON des traductions (format mpc-traductions-ar).")
        parser.add_argument("--dry-run", action="store_true", help="Affiche les changements prévus, n'écrit rien.")
        parser.add_argument("--slug", action="append", default=[], help="Limiter à ce produit (répétable).")

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.is_file():
            raise CommandError(f"Fichier introuvable : {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"JSON invalide : {exc}") from exc
        if data.get("format") != "mpc-traductions-ar":
            raise CommandError("Format attendu : mpc-traductions-ar.")
        rows = data.get("produits") or []
        if options["slug"]:
            rows = [r for r in rows if r.get("slug") in options["slug"]]
        slugs = [r.get("slug") for r in rows]
        if len(set(slugs)) != len(slugs):
            raise CommandError("Slug en double dans le fichier.")

        dry = options["dry_run"]
        products = {p.slug: p for p in Product.objects.filter(slug__in=slugs).prefetch_related("highlights")}
        self.stdout.write(self.style.MIGRATE_HEADING("APERÇU (--dry-run) : aucune écriture" if dry else "IMPORT"))
        plans, refused = [], []
        for row in rows:
            slug = row.get("slug")
            plan, reason = self.plan(row, products.get(slug))
            status = row.get("content_status", "")
            if reason:
                refused.append(slug)
                self.stdout.write(self.style.ERROR(f"\n✗ {slug} : {reason}"))
                continue
            label = f"\n{slug}  [statut : {status}]"
            if not plan["fields"] and not plan["highlights"]:
                self.stdout.write(f"{label} — aucun changement (contenu déjà identique)")
                continue
            self.stdout.write(self.style.MIGRATE_LABEL(label))
            for key, (old, new) in plan["fields"].items():
                self.stdout.write(f"  {key}\n    avant : {short(old)}\n    après : {short(new)}")
            for pos, (old, new) in plan["highlights"].items():
                self.stdout.write(f"  picto {pos + 1} (label_ar)\n    avant : {short(old)}\n    après : {short(new)}")
            if status != VALIDATED:
                note = "non validé : sera ignoré à l'import réel" if dry else "non validé : ignoré"
                self.stdout.write(self.style.WARNING(f"  ⚠ {note} (content_status ≠ « {VALIDATED} »)"))
                if not dry:
                    continue
            plans.append((plan["product"], plan))

        changed = [p for p in plans if p[1]["fields"] or p[1]["highlights"]]
        n_fields = sum(len(p["fields"]) + len(p["highlights"]) for _, p in changed)
        summary = f"\n{len(changed)} produit(s), {n_fields} champ(s) à modifier ; {len(refused)} refusé(s)."
        if dry or not changed:
            self.stdout.write(self.style.SUCCESS(summary + ("\nAucune donnée n'a été modifiée." if dry else "")))
            return
        backup = self.backup(path, changed)
        self.apply(changed)
        log_action(
            "product.import_traductions_ar",
            target_type="catalog.product",
            changes={"file": path.name, "products": [p.slug for p, _ in changed], "backup": backup.name},
        )
        self.stdout.write(self.style.SUCCESS(summary + f"\nÉcrit. Sauvegarde des anciennes valeurs : {backup}"))

    def plan(self, row, product):
        """Changements prévus pour un produit, ou (None, raison du refus)."""
        if product is None:
            return None, "produit introuvable dans la base (slug inconnu)"
        unknown = (
            set(row)
            - set(FIELDS)
            - {
                "slug",
                "content_status",
                "source_fr",
                "highlights_ar",
                "key_ingredients",
                "informations_manquantes",
                "a_verifier",
                "optimisation",
            }
        )
        if unknown:
            return None, f"champ(s) non autorisé(s) : {', '.join(sorted(unknown))}"
        source, now = row.get("source_fr") or {}, current_source(product)
        if set(source) != set(SOURCE_KEYS):
            return None, "« source_fr » incomplet"
        # Le français de la base doit être celui qui a été traduit (ou déjà la version optimisée du fichier).
        drift = [k for k in SOURCE_KEYS if now[k] != source[k] and now[k] != row.get(k, object())]
        if drift:
            return None, "le français de la base a changé depuis la traduction : " + ", ".join(drift)
        plan = {"product": product, "fields": {}, "highlights": {}}
        for key in FIELDS:
            if key not in row:
                continue
            new = clean(key, row[key], f"{product.slug}.{key}")
            old = getattr(product, key)
            if new is not None and new != old:
                plan["fields"][key] = (old, new)
        labels = row.get("highlights_ar") or []
        highlights = list(product.highlights.all())
        if labels:
            if len(labels) != len(highlights):
                return None, f"highlights_ar : {len(labels)} libellé(s) pour {len(highlights)} picto(s)"
            for i, (h, new) in enumerate(zip(highlights, labels, strict=True)):
                new = (new or "").strip()
                if len(new) > 60:
                    return None, f"highlights_ar[{i + 1}] : 60 caractères au maximum"
                if new and new != h.label_ar:
                    plan["highlights"][i] = (h.label_ar, new)
        return plan, None

    def backup(self, source_path, changed) -> Path:
        stamp = timezone.now().strftime("%Y%m%d-%H%M%S")
        path = source_path.with_name(f"{source_path.stem}.sauvegarde-{stamp}.json")
        data = {
            p.slug: {
                "fields": {k: old for k, (old, _) in plan["fields"].items()},
                "highlights_ar": {str(i + 1): old for i, (old, _) in plan["highlights"].items()},
            }
            for p, plan in changed
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    @transaction.atomic
    def apply(self, changed):
        for product, plan in changed:
            for key, (_, new) in plan["fields"].items():
                setattr(product, key, new)
            if plan["fields"]:
                product.save(update_fields=[*plan["fields"], "updated_at"])
            highlights = list(product.highlights.all())
            for i, (_, new) in plan["highlights"].items():
                highlights[i].label_ar = new
                highlights[i].save(update_fields=["label_ar"])
