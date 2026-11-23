"""
Classe les produits Jodhur (hors Shopify) dans les catégories par zone, et rend visibles des catégories choisies.
APERÇU par défaut : rien n'est écrit sans --appliquer.

    # 1. liste proposée (lecture seule) : produits ACTIFS qui n'auront plus de catégorie visible après
    #    le passage des besoins (Hydratation, Éclat, Anti-âge) en filtres
    python manage.py classer_produits --modele produits_jodhur.csv
    # 2. aperçu : classement (lignes « appliquer = oui ») + catégories rendues visibles
    python manage.py classer_produits --liste produits_jodhur.csv --rendre-visibles visage --report apercu.md
    # 3. application (après vérification)
    python manage.py classer_produits --liste produits_jodhur.csv --rendre-visibles visage --appliquer

Règles :
- proposition tirée UNIQUEMENT d'une donnée Jodhur du produit : son filtre « Zone d'application » (Admin → Filtres) ;
  sans cette donnée, aucune proposition (à classer à la main) ; jamais d'après la marque ou le fournisseur ;
- seules les lignes « appliquer = oui » sont appliquées ; une catégorie est AJOUTÉE, jamais retirée ni remplacée ;
- --rendre-visibles : seulement les catégories nommées ; l'aperçu signale celles qui n'auraient aucun produit
  actif (elles apparaîtraient vides dans le menu) ;
- rien d'autre n'est modifié (produits, prix, stock, filtres, autres catégories).
"""

import csv
import re
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from apps.audit.services import log_action
from apps.catalog.models import Category, Product, ProductCategory

NEEDS = ("hydratation", "eclat", "anti-age")
ZONE_GROUP = "zone d application"
# Option du filtre « Zone d'application » → (catégorie Jodhur, statut)
ZONE_TO_CATEGORY = {
    "visage": ("visage", "sûr"),
    "yeux": ("yeux", "sûr"),  # sous-catégorie Visage › Yeux (décision de la propriétaire)
    "levres": ("levres", "sûr"),
    "corps": ("corps", "sûr"),
    "cheveux": ("cheveux", "sûr"),
}
HEADER = ["identifiant_url", "produit", "statut_produit", "categories_actuelles", "donnee_jodhur_utilisee",
          "categorie_jodhur", "raison", "statut", "appliquer"]  # fmt: skip


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def _label(cat) -> str:
    return f"{cat.parent.name} › {cat.name}" if cat.parent_id else cat.name


def _visible(cat) -> bool:
    return cat.is_active and (cat.parent is None or cat.parent.is_active)


def _cell(value, size=150) -> str:
    text = str(value).replace("|", "/").replace("\n", " ")
    return text if len(text) <= size else text[: size - 1] + "…"


class Command(BaseCommand):
    help = "Classe les produits Jodhur par zone et rend visibles des catégories. Aperçu par défaut."

    def add_arguments(self, parser):
        parser.add_argument("--modele", help="Écrit la liste proposée (CSV) puis s'arrête. Aucune écriture en base.")
        parser.add_argument("--liste", help="Liste validée (CSV) : seules les lignes « appliquer = oui » comptent.")
        parser.add_argument("--rendre-visibles", default="", help="Identifiants URL des catégories à rendre visibles.")
        parser.add_argument("--besoins", default=",".join(NEEDS), help="Catégories besoin (futur filtre).")
        parser.add_argument("--appliquer", action="store_true", help="Écrit en base. Sans cette option : aperçu.")
        parser.add_argument("--report", help="Rapport Markdown.")

    def handle(self, *args, **opts):
        self.need_slugs = {s.strip() for s in opts["besoins"].split(",") if s.strip()}
        if opts["modele"]:
            self._write_model(Path(opts["modele"]))
            return
        if not opts["liste"] and not opts["rendre_visibles"]:
            raise CommandError("Indiquez --modele, --liste et/ou --rendre-visibles.")
        plan = self._plan(opts)
        if opts["appliquer"]:
            with transaction.atomic():
                self._apply(plan)
        report = self._render(plan, opts["appliquer"])
        if opts["report"]:
            Path(opts["report"]).write_text(report, encoding="utf-8")
        else:
            self.stdout.write(report)
        mode = "APPLIQUÉ" if opts["appliquer"] else "APERÇU (aucune écriture)"
        self.stdout.write(
            f"{mode} — {sum(1 for r in plan['rows'] if r['add'])} produit(s) classé(s),"
            f" {len(plan['visible'])} catégorie(s) rendue(s) visible(s)."
        )

    # --- Produits concernés et propositions ---------------------------------------------------------
    def _hidden_after_needs(self) -> set:
        needs = Category.objects.filter(slug__in=self.need_slugs)
        return set(needs.values_list("pk", flat=True)) | set(
            Category.objects.filter(parent__in=needs).values_list("pk", flat=True)
        )

    def _candidates(self):
        """Produits Jodhur ACTIFS qui n'auraient plus aucune catégorie visible après le passage des besoins."""
        hidden = self._hidden_after_needs()
        out = []
        products = Product.objects.filter(shopify_id__isnull=True, status=Product.Status.ACTIVE).order_by("position")
        for p in products.prefetch_related("filter_options__group"):
            links = list(ProductCategory.objects.filter(product=p).select_related("category__parent"))
            if not any(link.category_id not in hidden and _visible(link.category) for link in links):
                out.append((p, links))
        return out

    def _propose(self, product):
        zones = [o for o in product.filter_options.all() if _norm(o.group.name) == ZONE_GROUP]
        if not zones:
            return "", "aucune (pas de filtre « Zone d'application »)", "aucune donnée Jodhur : à classer à la main", ""
        cats, statuses = [], []
        for opt in zones:
            target = ZONE_TO_CATEGORY.get(_norm(opt.name).replace(" ", "-")) or ZONE_TO_CATEGORY.get(opt.slug)
            if target and target[0] not in cats:
                cats.append(target[0])
                statuses.append(target[1])
        used = "filtre Zone d'application : " + ", ".join(o.name for o in zones)
        if not cats:
            return "", used, "zone sans catégorie Jodhur correspondante", ""
        statut = "sûr" if all(s == "sûr" for s in statuses) else "à confirmer"
        why = "zone indiquée dans la fiche Jodhur"
        if "yeux" in cats:
            why += " ; « Yeux » → sous-catégorie Visage › Yeux"
        return " | ".join(cats), used, why, statut

    def _write_model(self, path: Path):
        rows = self._candidates()
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(HEADER)
            for p, links in rows:
                cat, used, why, statut = self._propose(p)
                w.writerow([p.slug, p.public_name, p.get_status_display(), ", ".join(_label(x.category) for x in links),
                            used, cat, why, statut or "incertain", "oui" if statut == "sûr" else "non"])  # fmt: skip
        self.stdout.write(f"Liste proposée : {path} ({len(rows)} produit(s)). Aucune écriture en base.")

    # --- Plan ---------------------------------------------------------------------------------------
    def _plan(self, opts) -> dict:
        by_slug = {c.slug: c for c in Category.objects.select_related("parent")}
        rows, errors = [], []
        if opts["liste"]:
            path = Path(opts["liste"])
            if not path.exists():
                raise CommandError(f"Liste introuvable : {path}")
            with path.open(encoding="utf-8-sig", newline="") as fh:
                for i, line in enumerate(csv.DictReader(fh, delimiter=";"), start=2):
                    slug = (line.get("identifiant_url") or "").strip()
                    if not slug:
                        continue
                    product = Product.objects.filter(slug=slug).first()
                    if product is None:
                        errors.append(f"ligne {i} : produit « {slug} » introuvable")
                        continue
                    wanted = []
                    for s in (v.strip() for v in (line.get("categorie_jodhur") or "").split("|") if v.strip()):
                        if s not in by_slug:
                            errors.append(f"ligne {i} : catégorie « {s} » introuvable")
                        else:
                            wanted.append(by_slug[s])
                    apply = _norm(line.get("appliquer") or "") == "oui"
                    if apply and not wanted:
                        errors.append(f"ligne {i} : « appliquer = oui » sans catégorie")
                    current = list(ProductCategory.objects.filter(product=product).select_related("category__parent"))
                    have = {link.category_id for link in current}
                    rows.append({
                        "product": product,
                        "current": [_label(link.category) for link in current],
                        "wanted": wanted,
                        "add": [c for c in wanted if c.pk not in have] if apply else [],
                        "apply": apply,
                        "used": (line.get("donnee_jodhur_utilisee") or "").strip(),
                        "why": (line.get("raison") or "").strip(),
                        "statut": (line.get("statut") or "").strip(),
                    })  # fmt: skip
        visible = []
        for s in (v.strip() for v in opts["rendre_visibles"].split(",") if v.strip()):
            if s not in by_slug:
                errors.append(f"--rendre-visibles : catégorie « {s} » introuvable")
                continue
            if s in self.need_slugs:
                errors.append(f"--rendre-visibles : « {s} » est un besoin (il devient un filtre)")
                continue
            visible.append(by_slug[s])
        if errors:
            raise CommandError("Refusé, rien n'a été fait :\n- " + "\n- ".join(errors))

        added = {}
        for r in rows:
            for c in r["add"]:
                added.setdefault(c.pk, []).append(r["product"])
        stats = []
        for c in visible:
            linked = Product.objects.filter(category_links__category=c).distinct()
            new = added.get(c.pk, [])
            active = {p.pk for p in linked.filter(status=Product.Status.ACTIVE)} | {
                p.pk for p in new if p.status == Product.Status.ACTIVE
            }
            drafts = {p.pk for p in linked.filter(status=Product.Status.DRAFT)}
            parent_hidden = c.parent_id and not c.parent.is_active and c.parent_id not in {v.pk for v in visible}
            stats.append({"cat": c, "active": len(active), "drafts": len(drafts), "parent_hidden": parent_hidden,
                          "already": c.is_active})  # fmt: skip

        # Simulation : produits Jodhur actifs encore sans catégorie visible après tout cela + passage des besoins.
        hidden = self._hidden_after_needs()
        shown = {c.pk for c in visible}
        orphans = []
        for p, links in self._candidates():
            extra = next((r["add"] for r in rows if r["product"].pk == p.pk), [])
            cats = [link.category for link in links] + extra

            def shows(c):
                if c.pk in hidden or not (c.is_active or c.pk in shown):
                    return False
                return c.parent is None or c.parent.is_active or c.parent_id in shown

            if not any(shows(c) for c in cats):
                orphans.append(p)
        return {"rows": rows, "visible": visible, "stats": stats, "orphans": orphans}

    # --- Application --------------------------------------------------------------------------------
    def _apply(self, plan):
        for r in plan["rows"]:
            if not r["add"]:
                continue
            start = (ProductCategory.objects.filter(product=r["product"]).aggregate(m=Max("position"))["m"] or -1) + 1
            for i, cat in enumerate(r["add"]):
                ProductCategory.objects.get_or_create(
                    product=r["product"], category=cat, defaults={"position": start + i}
                )
            log_action("product.classify", target=r["product"], changes={"categoriesAdded": [c.pk for c in r["add"]]})
        if plan["visible"]:
            Category.objects.filter(pk__in=[c.pk for c in plan["visible"]]).update(is_active=True)
            log_action(
                "category.show", target_type="catalog.category", changes={"slugs": [c.slug for c in plan["visible"]]}
            )

    # --- Rapport ------------------------------------------------------------------------------------
    def _render(self, plan, applied: bool) -> str:
        lines = [
            "# Classement des produits Jodhur et catégories visibles — "
            + ("APPLIQUÉ" if applied else "APERÇU (aucune écriture)"),
            "",
            "## 1. Produits Jodhur : catégorie proposée",
            "",
            "Seules les lignes « appliquer = oui » sont appliquées. Une catégorie est ajoutée, jamais retirée.",
            "",
            "| Produit | Catégories actuelles | Donnée Jodhur utilisée | Catégorie proposée | Raison | Statut"
            " | Appliqué |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in plan["rows"]:
            p = r["product"]
            if r["add"]:
                done = "oui → + " + ", ".join(c.name for c in r["add"])
            else:
                done = "oui (déjà classé)" if r["apply"] else "non"
            lines.append(
                f"| {_cell(p.public_name, 60)} (`{p.slug}`, {p.get_status_display()})"
                f" | {_cell(', '.join(r['current']) or '—')}"
                f" | {_cell(r['used'] or '—')} | {_cell(', '.join(_label(c) for c in r['wanted']) or '—')}"
                f" | {_cell(r['why'] or '—')} | **{r['statut'] or '—'}**"
                f" | {done} |"
            )
        lines += ["", "## 2. Catégories rendues visibles", ""]
        if not plan["stats"]:
            lines.append("- Aucune.")
        for s in plan["stats"]:
            c = s["cat"]
            warn = []
            if s["already"]:
                warn.append("déjà visible")
            if s["parent_hidden"]:
                warn.append(f"⚠️ sa catégorie parente « {c.parent.name} » reste masquée : elle restera invisible")
            if not s["active"]:
                warn.append("⚠️ aucun produit actif : apparaîtrait VIDE dans le menu")
            lines.append(
                f"- **{_label(c)}** (`{c.slug}`) : {s['active']} produit(s) actif(s) visibles sur la boutique,"
                f" {s['drafts']} brouillon(s) (invisibles tant qu'ils ne sont pas activés)"
                + (f" — {'; '.join(warn)}" if warn else "")
            )
        others = Category.objects.filter(is_active=False).exclude(pk__in=[c.pk for c in plan["visible"]])
        others = others.exclude(slug__in=self.need_slugs).exclude(parent__slug__in=self.need_slugs)
        if others.exists():
            lines += ["", "Restent MASQUÉES : " + ", ".join(_label(c) for c in others.select_related("parent")) + "."]
        lines += [
            "",
            "## 3. Vérification avant le passage des besoins en filtres",
            "",
            f"- Produits Jodhur ACTIFS qui n'auraient toujours aucune catégorie visible : **{len(plan['orphans'])}**",
        ]
        lines += [f"  - {p.public_name} (`{p.slug}`)" for p in plan["orphans"]]
        if not plan["orphans"]:
            lines.append("  → le passage des besoins en filtres ne retirera aucun produit actif du menu.")
        return "\n".join(lines) + "\n"
