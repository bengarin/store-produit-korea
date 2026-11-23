"""
Transforme les catégories « besoin » (Hydratation, Éclat, Anti-âge) en options du filtre « Besoin ».

    python manage.py besoins_en_filtres --report apercu.md --csv apercu.csv   # APERÇU : rien n'est écrit
    python manage.py besoins_en_filtres --appliquer --report rapport.md        # application

Ce que fait l'application (une seule transaction, rejouable sans doublon) :
- crée (ou reprend) le groupe de filtres « Besoin » et une option par catégorie besoin (même nom, même nom arabe) ;
- chaque produit rangé dans une catégorie besoin OU dans une de ses sous-catégories reçoit l'option correspondante
  (ex. « Éclat › Crèmes anti-taches » → filtre Besoin : Éclat) : son classement est conservé par le filtre ;
- les catégories besoin et leurs sous-catégories sont MASQUÉES (visible = non), jamais supprimées ; les liens
  produit ↔ catégorie sont CONSERVÉS (retour arrière possible en les rendant visibles) ;
- rien d'autre n'est modifié : ni produits, ni prix, ni stock, ni autres catégories, ni autres filtres.

L'aperçu signale : produits qui n'auraient plus AUCUNE catégorie visible, options de filtre ressemblantes qui
existent déjà dans d'autres groupes (non fusionnées), et liens du thème ou de la bannière vers ces catégories.
"""

import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.audit.services import log_action
from apps.catalog.models import Category, FilterGroup, FilterOption, ProductCategory
from apps.themes.models import HeroSlide, ThemeDraft, ThemeVersion

DEFAULT_NEEDS = "hydratation,eclat,anti-age"


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def _cell(value, size=120) -> str:
    text = str(value).replace("|", "/").replace("\n", " ")
    return text if len(text) <= size else text[: size - 1] + "…"


class Command(BaseCommand):
    help = "Catégories besoin (Hydratation, Éclat, Anti-âge) → filtre « Besoin ». Aperçu par défaut."

    def add_arguments(self, parser):
        parser.add_argument("--appliquer", action="store_true", help="Écrit en base. Sans cette option : aperçu.")
        parser.add_argument("--categories", default=DEFAULT_NEEDS, help="Identifiants URL des catégories besoin.")
        parser.add_argument("--groupe", default="besoin", help="Identifiant URL du groupe de filtres.")
        parser.add_argument("--groupe-nom", default="Besoin")
        parser.add_argument("--groupe-nom-ar", default="الاحتياج")
        parser.add_argument("--report", help="Rapport Markdown.")
        parser.add_argument("--csv", help="Détail produit par produit (CSV).")

    def handle(self, *args, **opts):
        slugs = [s.strip() for s in opts["categories"].split(",") if s.strip()]
        needs = list(Category.objects.filter(slug__in=slugs).select_related("parent"))
        missing = sorted(set(slugs) - {c.slug for c in needs})
        if missing:
            raise CommandError(f"Catégorie(s) introuvable(s) : {', '.join(missing)}. Rien n'a été fait.")
        if any(c.parent_id for c in needs):
            raise CommandError("Une catégorie besoin doit être une catégorie principale. Rien n'a été fait.")
        self.apply = opts["appliquer"]
        plan = self._plan(needs, opts)
        if self.apply:
            with transaction.atomic():
                self._apply(plan, opts)
        report = self._render(plan, opts)
        if opts["report"]:
            Path(opts["report"]).write_text(report, encoding="utf-8")
        else:
            self.stdout.write(report)
        if opts["csv"]:
            self._csv(Path(opts["csv"]), plan)
        mode = "APPLIQUÉ" if self.apply else "APERÇU (aucune écriture)"
        self.stdout.write(
            f"{mode} — {len(plan['products'])} produit(s) concerné(s), "
            f"{sum(1 for r in plan['products'] if r['add'])} filtre(s) à poser, "
            f"{sum(1 for r in plan['products'] if not r['after'])} sans catégorie visible après."
        )

    # --- Plan (lecture seule) -----------------------------------------------------------------------
    def _plan(self, needs, opts) -> dict:
        group = FilterGroup.objects.filter(slug=opts["groupe"]).first()
        existing_opts = {o.slug: o for o in group.options.all()} if group else {}
        children = {c.pk: c for c in Category.objects.filter(parent__in=needs).select_related("parent")}
        need_of = {c.pk: c for c in needs} | {pk: c.parent for pk, c in children.items()}
        hidden = [*needs, *children.values()]

        options = []
        for need in needs:
            opt = existing_opts.get(need.slug)
            options.append({"need": need, "option": opt, "state": "existe déjà" if opt else "à créer"})
        by_need = {o["need"].pk: o for o in options}

        similar = []
        for other in FilterOption.objects.select_related("group").exclude(group__slug=opts["groupe"]):
            words = set(_norm(other.name).split()) - {"anti", "et", "de", "des", "soin", "soins"}
            for need in needs:
                if set(_norm(need.name).split()) & words:
                    similar.append((other, need))

        links = (
            ProductCategory.objects.filter(category_id__in=need_of.keys())
            .select_related("product", "category__parent")
            .order_by("product__position", "product_id")
        )
        per_product = {}
        for link in links:
            per_product.setdefault(link.product_id, {"product": link.product, "links": []})["links"].append(link)
        rows = []
        for data in per_product.values():
            product = data["product"]
            current = list(
                ProductCategory.objects.filter(product=product).select_related("category__parent").order_by("position")
            )
            needs_here = []
            for link in data["links"]:
                need = need_of[link.category_id]
                if need not in needs_here:
                    needs_here.append(need)
            have = set(product.filter_options.values_list("pk", flat=True))
            add = [n for n in needs_here if not (by_need[n.pk]["option"] and by_need[n.pk]["option"].pk in have)]
            hidden_pks = {c.pk for c in hidden}
            remaining = [link.category for link in current if link.category_id not in hidden_pks]
            after = [c for c in remaining if c.is_active and (c.parent is None or c.parent.is_active)]
            masked = [c for c in remaining if c not in after]
            rows.append({
                "product": product,
                "current": [_label(link.category) for link in current],
                "needs": needs_here,
                "add": add,
                "after": [_label(c) for c in after],
                "masked": [_label(c) for c in masked],
                "shopify": bool(product.shopify_id),
            })  # fmt: skip
        return {
            "group": group,
            "needs": needs,
            "children": list(children.values()),
            "options": options,
            "similar": similar,
            "products": rows,
            "refs": self._theme_refs([c.slug for c in hidden]),
        }

    def _theme_refs(self, slugs) -> list[str]:
        """Liens du thème (publié + brouillon) et de la bannière qui pointent vers ces catégories."""
        found = []

        def walk(node, where):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "category" and value in slugs:
                        found.append(f"{where} : section liée à la catégorie « {value} »")
                    walk(value, where)
            elif isinstance(node, list):
                for value in node:
                    walk(value, where)
            elif isinstance(node, str):
                for slug in slugs:
                    if re.search(rf"categorie={re.escape(slug)}(?![\w-])", node):
                        found.append(f"{where} : lien « {node} »")

        published = ThemeVersion.objects.order_by("-number").first()
        if published:
            walk(published.data, f"thème publié (version {published.number})")
        draft = ThemeDraft.objects.first()
        if draft:
            walk(draft.data, "brouillon du thème")
        for slide in HeroSlide.objects.all():
            walk(slide.button_link, f"bannière d'accueil « {slide.title_fr} »")
        return sorted(set(found))

    # --- Application --------------------------------------------------------------------------------
    def _apply(self, plan, opts):
        group = plan["group"] or FilterGroup.objects.create(
            slug=opts["groupe"],
            name=opts["groupe_nom"][:80],
            name_ar=opts["groupe_nom_ar"][:80],
            position=(FilterGroup.objects.count()),
        )
        options = {}
        for i, entry in enumerate(plan["options"]):
            need = entry["need"]
            opt, _ = FilterOption.objects.get_or_create(
                group=group,
                slug=need.slug,
                defaults={"name": need.name[:80], "name_ar": (need.name_ar or "")[:80], "position": i},
            )
            options[need.pk] = opt
        for row in plan["products"]:
            for need in row["needs"]:
                options[need.pk].products.add(row["product"])
        hidden = [*plan["needs"], *plan["children"]]
        Category.objects.filter(pk__in=[c.pk for c in hidden]).update(is_active=False)
        log_action(
            "catalog.needs_to_filters",
            target_type="catalog.filtergroup",
            target_id=str(group.pk),
            changes={
                "categoriesHidden": [c.slug for c in hidden],
                "products": len(plan["products"]),
                "options": {o.slug: o.pk for o in options.values()},
            },
        )

    # --- Rapport ------------------------------------------------------------------------------------
    def _render(self, plan, opts) -> str:
        rows = plan["products"]
        orphans = [r for r in rows if not r["after"] and not r["masked"]]
        only_masked = [r for r in rows if not r["after"] and r["masked"]]
        per_need = Counter(n.name for r in rows for n in r["needs"])
        title = "APPLIQUÉ" if self.apply else "APERÇU (aucune écriture)"
        group = plan["group"]
        lines = [
            f"# Besoins → filtre « {opts['groupe_nom']} » — {title}",
            "",
            "## Comment le filtre conserve le classement",
            "",
            f"- Groupe de filtres « {opts['groupe_nom']} » ({opts['groupe_nom_ar']}) :"
            f" {'existe déjà' if group else 'à créer (visible)'} — identifiant `{opts['groupe']}`.",
            "- Une option par catégorie besoin, même nom et même nom arabe que la catégorie :",
        ]
        for entry in plan["options"]:
            need = entry["need"]
            lines.append(
                f"  - **{need.name}** ({need.name_ar or 'nom arabe vide'}) → option `{opts['groupe']}:{need.slug}`"
                f" — {entry['state']} — {per_need[need.name]} produit(s)"
            )
        lines += [
            "- Chaque produit rangé dans la catégorie besoin OU dans une de ses sous-catégories reçoit l'option :"
            " sur la boutique, « Produits » → filtre « Besoin » → « Éclat » affiche exactement ces produits"
            f" (adresse : `/produits?filtres={opts['groupe']}:eclat`).",
            "- Les catégories besoin et leurs sous-catégories sont MASQUÉES, pas supprimées ; les liens produit ↔"
            " catégorie sont GARDÉS : pour revenir en arrière, il suffit de les rendre visibles.",
            "",
            "## Catégories masquées",
            "",
        ]
        lines += [f"- {_label(c)}" for c in [*plan["needs"], *plan["children"]]]
        if plan["children"]:
            lines += [
                "",
                "⚠️ Les sous-catégories (ex. « Contour des yeux ») décrivent un TYPE de produit : masquées avec leur"
                " besoin ; leurs produits gardent le filtre du besoin parent. À recréer sous Visage si vous le"
                " souhaitez (non fait automatiquement).",
            ]
        lines += ["", "## Points à vérifier", ""]
        lines.append(
            f"- Produits sans AUCUNE autre catégorie : **{len(orphans)}** sur {len(rows)} (trouvables par le"
            " filtre seulement ; une catégorie est obligatoire pour activer un produit en brouillon)."
        )
        lines.append(
            f"- Produits dont les autres catégories sont toutes MASQUÉES : **{len(only_masked)}** (invisibles dans le"
            " menu tant que ces catégories restent masquées ; trouvables par le filtre)."
        )
        if plan["similar"]:
            lines.append("- Options ressemblantes dans d'autres groupes de filtres (NON fusionnées, à vérifier) :")
            lines += [f"  - « {o.group.name} › {o.name} » ↔ besoin « {n.name} »" for o, n in plan["similar"]]
        else:
            lines.append("- Aucune option ressemblante dans d'autres groupes de filtres.")
        if plan["refs"]:
            lines.append("- Liens du thème / de la bannière vers ces catégories (ne filtreront plus, à modifier) :")
            lines += [f"  - {r}" for r in plan["refs"]]
        else:
            lines.append("- Aucun lien du thème ou de la bannière vers ces catégories.")
        lines += [
            "",
            "## Détail produit par produit",
            "",
            "| Produit | Statut | Origine | Catégories actuelles | Filtre « Besoin » posé"
            " | Catégories visibles après | Catégories masquées restantes | Alerte |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in rows:
            p = r["product"]
            have = [n.name for n in r["needs"] if n not in r["add"]]
            filt = ", ".join(n.name for n in r["add"]) or "—"
            if have:
                filt += f" (déjà : {', '.join(have)})"
            lines.append(
                f"| {_cell(p.public_name, 60)} (`{p.slug}`) | {p.get_status_display()} |"
                f" {'Shopify' if r['shopify'] else 'Jodhur'} | {_cell(', '.join(r['current']))} | {_cell(filt)}"
                f" | {_cell(', '.join(r['after']) or 'aucune')} | {_cell(', '.join(r['masked']) or '—')} |"
                f" {_alert(r)} |"
            )
        return "\n".join(lines) + "\n"

    def _csv(self, path: Path, plan):
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["produit", "identifiant_url", "statut", "origine", "categories_actuelles", "filtre_besoin",
                        "categories_visibles_apres", "categories_masquees_restantes", "alerte"])  # fmt: skip
            for r in plan["products"]:
                p = r["product"]
                w.writerow([p.public_name, p.slug, p.get_status_display(), "Shopify" if r["shopify"] else "Jodhur",
                            ", ".join(r["current"]), ", ".join(n.name for n in r["needs"]), ", ".join(r["after"]),
                            ", ".join(r["masked"]), _alert(r)])  # fmt: skip


def _alert(r) -> str:
    if r["after"]:
        return "—"
    return "⚠️ seulement des catégories masquées" if r["masked"] else "⚠️ aucune autre catégorie"


def _label(cat) -> str:
    return f"{cat.parent.name} › {cat.name}" if cat.parent_id else cat.name
