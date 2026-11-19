"""
Importe les produits ACTIFS de Shopify dans le catalogue Jodhur, à partir d'un export en lecture seule
(backend/catalog_import/shopify/produits_actifs.json). Shopify n'est jamais modifié.

    python manage.py import_shopify --dry-run --report apercu_shopify.md   # aperçu : AUCUNE écriture
    python manage.py import_shopify --report rapport_shopify.md            # import réel + rapport

Règles :
- aucun doublon : un produit dont l'identifiant Shopify est déjà en base est IGNORÉ (jamais mis à jour : les
  modifications faites dans l'admin sont conservées) ; un produit local de même identifiant URL ou de même nom
  est signalé « doublon possible » et n'est pas importé ;
- produit créé en BROUILLON (rien n'apparaît sur la boutique sans relecture) ; fournisseur = « Vendor » Shopify ;
  marque laissée vide (Shopify n'en fournit pas) ; aucune donnée inventée ;
- variantes, prix, prix barrés et stock Shopify conservés ; chaque stock importé est tracé (« Premier comptage ») ;
  SKU repris s'il existe et n'est pas déjà utilisé ;
- images téléchargées depuis cdn.shopify.com (HTTPS uniquement), ré-encodées en WebP ; une image en échec est
  signalée, le produit est quand même créé ;
- catégories : seulement si une catégorie Jodhur porte EXACTEMENT le nom d'une collection ou de la catégorie
  Shopify ; sinon aucune (à choisir dans l'admin).
"""

import json
import re
import unicodedata
import urllib.request
from collections import Counter
from decimal import Decimal
from html import unescape
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from apps.audit.services import log_action
from apps.catalog.models import (
    Category,
    Product,
    ProductCategory,
    ProductImage,
    ProductOption,
    ProductOptionValue,
    Variant,
    VariantOptionValue,
)
from apps.catalog.services import unique_slug
from apps.core.html import sanitize_html
from apps.inventory.models import StockMovement
from apps.media_library.processing import ImageRejected
from apps.media_library.services import create_from_upload

DEFAULT_SOURCE = Path(settings.BASE_DIR) / "catalog_import" / "shopify" / "produits_actifs.json"
IMAGE_HOST = "https://cdn.shopify.com/"
OPTION_NAMES = {"size": "Taille"}  # nom technique Shopify → libellé affiché
DEFAULT_TITLE = "Default Title"
NOTE = "Import Shopify"


def _plain(html: str) -> str:
    text = re.sub(r"<(br|/p|/li|/h[1-6]|/div)[^>]*>", "\n", html or "", flags=re.I)
    text = unescape(re.sub(r"<[^>]+>", "", text))
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _first_paragraph(html: str) -> str:
    """Premier paragraphe du texte Shopify (repris tel quel, rien n'est rédigé)."""
    lines = _plain(html).split("\n")
    return lines[0][:1000] if lines and lines[0] else ""


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def _supplier_key(name: str) -> str:
    """Clé pour repérer des fournisseurs PROBABLEMENT identiques écrits différemment (signalés, jamais fusionnés)."""
    words = [w for w in _norm(name).split() if w not in {"cooperative", "agricole", "al", "el", "des", "de"}]
    return " ".join(words).replace("outour", "otor")


def _real_options(p: dict) -> list[dict]:
    return [o for o in p["options"] if not (o["name"] == "Title" and o["values"] == [DEFAULT_TITLE])]


def _download(url: str, timeout=30) -> bytes:
    if not url.startswith(IMAGE_HOST):
        raise ValueError("adresse d'image refusée (cdn.shopify.com uniquement)")
    req = urllib.request.Request(url, headers={"User-Agent": "Jodhur-import/1.0"})  # noqa: S310 (hôte vérifié)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (hôte vérifié ci-dessus)
        data = resp.read(settings.MEDIA_MAX_UPLOAD_BYTES + 1)
    if len(data) > settings.MEDIA_MAX_UPLOAD_BYTES:
        raise ValueError("image trop lourde")
    return data


class Command(BaseCommand):
    help = "Importe les produits actifs Shopify (export en lecture seule) en brouillons, sans doublon."

    def add_arguments(self, parser):
        parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="Fichier JSON exporté de Shopify.")
        parser.add_argument("--dry-run", action="store_true", help="Aperçu : aucune écriture, aucun téléchargement.")
        parser.add_argument("--report", help="Écrit le rapport (Markdown) dans ce fichier.")
        parser.add_argument("--csv", help="Écrit l'aperçu produit par produit (CSV) dans ce fichier.")
        parser.add_argument("--sans-images", action="store_true", help="N'importe pas les images (essais hors ligne).")

    def handle(self, *args, **opts):
        path = Path(opts["source"])
        if not path.exists():
            raise CommandError(f"Fichier introuvable : {path}")
        doc = json.loads(path.read_text(encoding="utf-8"))
        products = doc.get("products") or []
        if not products:
            raise CommandError("Aucun produit dans le fichier.")
        if any(p.get("status") != "ACTIVE" for p in products):
            raise CommandError("Le fichier contient des produits non actifs : export refusé.")
        self.dry = opts["dry_run"]
        self.with_images = not opts["sans_images"]
        self.categories = {c.name.strip().lower(): c for c in Category.objects.all()}

        rows = [self._analyse(p) for p in products]
        self._flag_source_duplicates(products, rows)
        if not self.dry:
            for p, row in zip(products, rows, strict=True):
                if row["action"] == "créer":
                    self._create(p, row)
        report = self._render(doc, products, rows)
        if opts["report"]:
            Path(opts["report"]).write_text(report, encoding="utf-8")
        if opts["csv"]:
            self._csv(Path(opts["csv"]), rows)
        counts = Counter(r["action"] for r in rows)
        mode = "APERÇU (aucune écriture)" if self.dry else "IMPORT"
        self.stdout.write(f"{mode} — " + ", ".join(f"{k} : {v}" for k, v in sorted(counts.items())))
        if not opts["report"]:
            self.stdout.write(report)

    # --- Analyse (aucune écriture) ----------------------------------------------------------------
    def _analyse(self, p: dict) -> dict:
        warnings = []
        row = {
            "title": p["title"],
            "handle": p["handle"],
            "vendor": p.get("vendor") or "",
            "shopify_id": p["id"],
            "category": p.get("category") or "",
            "collections": p.get("collections") or [],
            "images": len(p.get("images") or []),
            "variants": [],
            "warnings": warnings,
            "action": "créer",
        }
        existing = Product.objects.filter(shopify_id=p["id"]).first()
        if existing:
            row["action"] = "déjà importé (ignoré)"
            row["local"] = existing.slug
            return row
        same = Product.objects.filter(slug=p["handle"]).first() or (
            Product.objects.filter(name__iexact=p["title"].strip()).first()
            or Product.objects.filter(display_name__iexact=p["title"].strip()).first()
        )
        if same:
            row["action"] = "doublon possible (non importé)"
            row["local"] = same.slug
            local = same.public_name.strip()
            warnings.append(f"produit local « {local} » ({same.slug}) : même identifiant URL ou même nom")
        if not row["vendor"]:
            warnings.append("fournisseur manquant")
        if not row["images"]:
            warnings.append("aucune image")
        if not _plain(p.get("descriptionHtml")):
            warnings.append("description manquante")
        cats = self._matching_categories(p)
        row["jodhur_categories"] = [c.name for c in cats]
        if not cats:
            warnings.append("catégorie Jodhur à choisir (aucune correspondance exacte)")
        warnings.append("marque à renseigner (Shopify n'en fournit pas)")
        used_skus = set()
        for v in p["variants"]:
            sku = (v.get("sku") or "").strip()
            info = {
                "title": "" if v["title"] == DEFAULT_TITLE else v["title"],
                "sku": sku,
                "price": v["price"],
                "compare": v.get("compareAtPrice"),
                "stock": v.get("inventoryQuantity") if v.get("tracked") else "non suivi",
            }
            if not sku:
                info["sku_note"] = "SKU manquant"
            elif Variant.objects.filter(sku=sku).exists() or sku in used_skus:
                info["sku_note"] = f"SKU « {sku} » déjà utilisé : non repris"
                info["sku"] = ""
            elif sku.isdigit() and len(sku) < 3:
                info["sku_note"] = f"SKU « {sku} » suspect (à vérifier)"
            used_skus.add(sku)
            if Decimal(v["price"]) <= 0:
                warnings.append(f"prix à 0 ({info['title'] or 'variante'})")
            if v.get("tracked") and v.get("inventoryQuantity") is None:
                warnings.append("stock manquant")
            elif v.get("tracked") and v["inventoryQuantity"] <= 0:
                info["stock_note"] = "rupture"
            row["variants"].append(info)
        missing_sku = sum(1 for v in row["variants"] if v.get("sku_note") == "SKU manquant")
        if missing_sku:
            warnings.append(f"SKU manquant ({missing_sku}/{len(row['variants'])} variante(s))")
        return row

    def _matching_categories(self, p: dict) -> list:
        names = [*(p.get("collections") or [])]
        if p.get("category"):
            names.append(p["category"].split(">")[-1])
        found = []
        for name in names:
            cat = self.categories.get(name.strip().lower())
            if cat and cat not in found:
                found.append(cat)
        return found

    def _flag_source_duplicates(self, products, rows):
        titles = Counter(p["title"].strip().lower() for p in products)
        for p, row in zip(products, rows, strict=True):
            n = titles[p["title"].strip().lower()]
            if n > 1:
                row["warnings"].append(
                    f"même nom que {n - 1} autre(s) produit(s) Shopify (fournisseur : {row['vendor']})"
                )
        groups = {}
        for v in {p.get("vendor") or "" for p in products}:
            groups.setdefault(_supplier_key(v), set()).add(v)
        self.supplier_groups = [sorted(g) for g in groups.values() if len(g) > 1]

    # --- Création (une transaction par produit) ----------------------------------------------------
    def _create(self, p: dict, row: dict):
        media = []
        if self.with_images:
            for i, img in enumerate(p.get("images") or []):
                try:
                    data = _download(img["url"])
                    name = f"shopify-{p['handle']}-{i + 1}.img"
                    alt = (img.get("alt") or p["title"])[:255]
                    asset, _ = create_from_upload(ContentFile(data, name=name), alt=alt)
                    media.append((img, asset))
                except (OSError, ValueError, ImageRejected) as exc:
                    row["warnings"].append(f"image {i + 1} non importée ({exc})")
        try:
            with transaction.atomic():
                product = self._create_product(p, row, media)
        except Exception as exc:  # noqa: BLE001 — un produit en échec n'arrête pas l'import
            row["action"] = "échec"
            row["warnings"].append(f"erreur : {exc}")
            return
        row["action"] = "créé (brouillon)"
        row["local"] = product.slug

    def _create_product(self, p: dict, row: dict, media) -> Product:
        position = (Product.objects.aggregate(m=Max("position"))["m"] or 0) + 1
        product = Product.objects.create(
            slug=unique_slug(p["handle"], Product),
            position=position,
            brand="",
            supplier=(p.get("vendor") or "")[:150],
            shopify_id=p["id"],
            name=p["title"][:200],
            display_name=p["title"][:255],
            summary=_first_paragraph(p.get("descriptionHtml")),
            description_html=sanitize_html(p.get("descriptionHtml") or ""),
            status=Product.Status.DRAFT,
        )
        for i, cat in enumerate(self._matching_categories(p)):
            ProductCategory.objects.create(product=product, category=cat, position=i)

        images_by_url = {}
        for i, (img, asset) in enumerate(media):
            pi = ProductImage.objects.create(
                product=product, media=asset, alt=(img.get("alt") or p["title"])[:255], position=i, in_gallery=True
            )
            images_by_url[img["url"].split("?")[0]] = pi

        options = _real_options(p)
        multi = len(p["variants"]) > 1
        values = {}
        if multi:
            for oi, opt in enumerate(options):
                option = ProductOption.objects.create(
                    product=product, name=OPTION_NAMES.get(opt["name"], opt["name"])[:50], position=oi
                )
                for vi, value in enumerate(opt["values"]):
                    values[(opt["name"], value)] = ProductOptionValue.objects.create(
                        option=option, value=value[:50], position=vi
                    )

        for i, (v, info) in enumerate(zip(p["variants"], row["variants"], strict=True)):
            tracked = bool(v.get("tracked"))
            stock = v.get("inventoryQuantity") if tracked else None
            compare = v.get("compareAtPrice")
            variant = Variant.objects.create(
                product=product,
                shopify_id=v["id"],
                title=info["title"][:160],
                sku=info["sku"] or None,
                price=Decimal(v["price"]),
                compare_at_price=Decimal(compare) if compare and Decimal(compare) > Decimal(v["price"]) else None,
                stock_quantity=stock,
                track_inventory=tracked,
                position=i,
                is_default=i == 0,
                image=images_by_url.get((v.get("imageUrl") or "").split("?")[0]),
            )
            if multi:
                VariantOptionValue.objects.bulk_create(
                    [
                        VariantOptionValue(variant=variant, option_value=values[(o["name"], o["value"])])
                        for o in v.get("options") or []
                        if (o["name"], o["value"]) in values
                    ]
                )
            if stock is not None:
                StockMovement.objects.create(
                    variant=variant,
                    delta=stock,
                    quantity_before=None,
                    quantity_after=stock,
                    reason=StockMovement.Reason.INITIAL_COUNT,
                    note=NOTE,
                )
        log_action(
            "product.import_shopify",
            target=product,
            changes={"shopifyId": p["id"], "supplier": product.supplier, "variants": len(p["variants"])},
        )
        return product

    # --- Rapport ------------------------------------------------------------------------------------
    def _render(self, doc, products, rows) -> str:
        counts = Counter(r["action"] for r in rows)
        variants = [v for r in rows for v in r["variants"]]
        lines = [
            f"# Import Shopify → Jodhur — {'APERÇU (aucune écriture)' if self.dry else 'RAPPORT'}",
            "",
            f"Source : {doc.get('source', '?')} · boutique {doc.get('shop', '?')}"
            f" · export du {doc.get('exportedAt', '?')}"
            f" · {len(products)} produits actifs · {len(variants)} variantes"
            f" · {sum(r['images'] for r in rows)} images.",
            "",
            "Actions : " + " · ".join(f"**{k}** : {v}" for k, v in sorted(counts.items())),
            "",
            "Règles : produits créés en brouillon ; fournisseur = « Vendor » Shopify ; aucun produit existant modifié ;"
            " Shopify jamais modifié.",
            "",
            "## Données manquantes",
            "",
            f"- SKU manquant : {sum(1 for v in variants if v.get('sku_note') == 'SKU manquant')} variante(s) sur"
            f" {len(variants)}",
            f"- Catégorie Jodhur à choisir : {sum(1 for r in rows if not r.get('jodhur_categories'))} produit(s)",
            "- Marque : à renseigner pour tous les produits (Shopify n'a pas de champ marque ; non devinée)",
            f"- Stock à 0 (rupture) : {sum(1 for v in variants if v.get('stock_note') == 'rupture')} variante(s)",
            f"- Sans image : {sum(1 for r in rows if not r['images'])} · sans fournisseur :"
            f" {sum(1 for r in rows if not r['vendor'])}",
            "",
            "## Doublons possibles",
            "",
        ]
        dup_local = [r for r in rows if r["action"].startswith("doublon")]
        lines += [f"- **{r['title']}** ↔ produit local `{r['local']}` (non importé)" for r in dup_local] or [
            "- Aucun doublon avec le catalogue Jodhur actuel."
        ]
        same_names = sorted({r["title"] for r in rows if any(w.startswith("même nom") for w in r["warnings"])})
        if same_names:
            lines += ["", "Même nom dans Shopify (produits distincts, importés tous les deux) :"]
            lines += [
                f"- {t} — " + ", ".join(f"{r['vendor']} (`{r['handle']}`)" for r in rows if r["title"] == t)
                for t in same_names
            ]
        if self.supplier_groups:
            lines += ["", "Fournisseurs probablement identiques écrits différemment (NON fusionnés, à vérifier) :"]
            lines += ["- " + " · ".join(f"« {g} »" for g in group) for group in self.supplier_groups]
        lines += ["", "## Fournisseurs", ""]
        lines += [f"- {v} : {n} produit(s)" for v, n in Counter(r["vendor"] for r in rows).most_common()]
        lines += [
            "",
            "## Produits",
            "",
            "| Produit | Fournisseur | Variantes (titre · SKU · prix DH · stock) | Images | Catégorie Shopify"
            " | Catégorie Jodhur | Action | Points à vérifier |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in rows:
            vs = "<br>".join(
                f"{v['title'] or '—'} · {v['sku'] or 'sans SKU'} · {v['price']}"
                + (f" (barré {v['compare']})" if v["compare"] else "")
                + f" · {v['stock']}"
                for v in r["variants"]
            )
            notes = "; ".join(
                w for w in r["warnings"] if not w.startswith(("marque", "SKU manquant", "catégorie Jodhur"))
            )
            lines.append(
                f"| {_cell(r['title'])} | {_cell(r['vendor'])} | {vs} | {r['images']} | {_cell(r['category'] or '—')}"
                f" | {_cell(', '.join(r.get('jodhur_categories') or []) or '—')} | {r['action']}"
                f" | {_cell(notes or '—')} |"
            )
        return "\n".join(lines) + "\n"

    def _csv(self, path: Path, rows):
        import csv

        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(
                ["produit", "handle", "fournisseur", "variante", "sku", "prix", "prix_barre", "stock", "images",
                 "categorie_shopify", "collections_shopify", "categorie_jodhur", "action", "a_verifier"]
            )  # fmt: skip
            for r in rows:
                for v in r["variants"]:
                    w.writerow(
                        [r["title"], r["handle"], r["vendor"], v["title"], v["sku"], v["price"], v["compare"] or "",
                         v["stock"], r["images"], r["category"], " | ".join(r["collections"]),
                         ", ".join(r.get("jodhur_categories") or []), r["action"],
                         "; ".join(r["warnings"] + [v.get("sku_note", ""), v.get("stock_note", "")]).strip("; ")]
                    )  # fmt: skip


def _cell(value, size=80) -> str:
    text = str(value).replace("|", "/").replace("\n", " ")
    return text if len(text) <= size else text[: size - 1] + "…"
