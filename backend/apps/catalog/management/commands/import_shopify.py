"""
Import COMPLET des produits ACTIFS de Shopify dans Jodhur — une seule commande, relançable sans doublon.

    python manage.py import_shopify --rendre-visibles utiles --report apercu.md --csv apercu.csv   # APERÇU
    python manage.py import_shopify --rendre-visibles utiles --appliquer --report rapport.md --csv rapport.csv

`--rendre-visibles utiles` : avant d'activer les produits, rend visibles les catégories proposées (nouvelles
catégories) qui contiendront au moins un produit actif ; les catégories masquées à la main ne sont pas touchées.

Source : par défaut l'export complet versionné (catalog_import/shopify/export_shopify_complet.json) ;
`--source shopify` lit directement l'API Admin (pagination ; variables SHOPIFY_STORE_DOMAIN, SHOPIFY_ADMIN_TOKEN,
SHOPIFY_API_VERSION ; lecture seule) — `--export fichier.json` enregistre alors ce qui a été lu.

Ce qui est importé (détail champ par champ : catalog_import/shopify/CORRESPONDANCE_CHAMPS.md) :
- produit : nom, description, marque + fournisseur (Vendor), type, catégorie Shopify, collections, tags, SEO, handle ;
- variantes : options, SKU, code-barres, prix, prix barré, stock disponible, suivi du stock, vente sans stock, poids ;
- images : toutes, dans l'ordre, avec leur texte alternatif, TÉLÉCHARGÉES dans le stockage du projet (MEDIA_ROOT),
  ré-encodées ; la fiche n'utilise jamais l'adresse Shopify ; doublons évités (identifiant Shopify + empreinte) ;
- metafields : tous (identifiant, type, valeur brute), visibles dans l'admin ; certains alimentent aussi les champs
  Jodhur (ingrédients, bienfaits, utilisation, phrase courte, types de peau) ;
- catégories : uniquement par les correspondances EXPLICITES (tableau, nouvelles catégories, liste produit par
  produit) ; toute valeur sans correspondance est listée dans le rapport ;
- statut : un produit actif dans Shopify est ACTIF dans Jodhur s'il remplit les conditions d'activation ; sinon il
  reste en brouillon et le rapport donne le champ manquant, produit par produit.

Produits déjà présents : chaque champ venant de Shopify n'est remplacé que s'il n'a PAS été modifié dans Jodhur
depuis le dernier import (comparaison avec la dernière valeur importée) ; sinon la valeur Jodhur est gardée et
signalée. Rien n'est jamais supprimé (images, variantes, catégories, metafields) ; un produit archivé ou mis en
brouillon à la main dans Jodhur garde son statut. Shopify n'est jamais modifié.
"""

import csv
import json
import os
import re
import time
import unicodedata
import urllib.request
from collections import Counter
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from apps.audit.models import AuditLog
from apps.audit.services import log_action
from apps.catalog import services
from apps.catalog.models import (
    Category,
    Collection,
    Product,
    ProductCategory,
    ProductImage,
    ProductMetafield,
    ProductOption,
    ProductOptionValue,
    Variant,
    VariantOptionValue,
)
from apps.catalog.services import unique_slug
from apps.catalog.shopify_import import source as src
from apps.core.html import sanitize_html
from apps.inventory.models import StockMovement
from apps.media_library.processing import ImageRejected
from apps.media_library.services import create_from_upload

DATA_DIR = Path(settings.BASE_DIR) / "catalog_import" / "shopify"
DEFAULTS = {
    "source": DATA_DIR / "export_shopify_complet.json",
    "correspondances": DATA_DIR / "correspondances_proposees.csv",
    "nouvelles_categories": DATA_DIR / "nouvelles_categories_proposees.csv",
    "categories_produits": DATA_DIR / "produits_sans_categorie_proposes.csv",
    "base_precedente": DATA_DIR / "produits_actifs.json",
}
IMAGE_HOST = "https://cdn.shopify.com/"
OPTION_NAMES = {"size": "Taille"}
NOTE = "Import Shopify"
ACTION_CREATE = "product.import_shopify"
ACTION_UPDATE = "product.import_shopify_update"
MAPPING_HEADER = ["collection_shopify", "type", "produits", "exemples_produits", "correspondance_nom_identique",
                  "categorie_jodhur", "statut", "raison"]  # fmt: skip
# Metafields Shopify qui alimentent un champ Jodhur (namespace.key → champ, conversion).
METAFIELD_FIELDS = {
    "custom.ingredients": ("ingredients", "lines"),
    "custom.les_benefices": ("benefits", "bullets"),
    "custom.utilisation": ("usage_steps", "lines"),
    "custom.description_courte": ("short_description", "text160"),
    "custom.type_de_peau": ("skin_types", "text255"),
}
PRODUCT_FIELDS = ["name", "display_name", "brand", "supplier", "summary", "description_html", "short_description",
                  "ingredients", "benefits", "usage_steps", "skin_types", "seo_title", "seo_description"]  # fmt: skip
FIELD_LABELS = {
    "name": "nom", "display_name": "nom affiché", "brand": "marque", "supplier": "fournisseur",
    "summary": "description", "description_html": "description longue", "short_description": "phrase courte",
    "ingredients": "ingrédients", "benefits": "bienfaits", "usage_steps": "utilisation", "skin_types": "types de peau",
    "seo_title": "titre SEO", "seo_description": "méta-description", "title": "titre", "sku": "SKU",
    "barcode": "code-barres", "price": "prix", "compare_at_price": "prix barré", "stock_quantity": "stock",
    "track_inventory": "suivi du stock", "allow_backorder": "vente sans stock", "weight_grams": "poids",
}  # fmt: skip
CREATED = "créé"
UPDATE = "mis à jour"
LINK = "relié + mis à jour"
DUP = "doublon possible (non importé)"


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def _supplier_key(name: str) -> str:
    words = [w for w in _norm(name).split() if w not in {"cooperative", "agricole", "al", "el", "des", "de"}]
    return " ".join(words).replace("outour", "otor")


def _empty(value) -> bool:
    return value in (None, "", [], {})


def _json(value):
    """Valeur comparable / stockable en JSON (Decimal → texte)."""
    if isinstance(value, Decimal):
        return str(value.quantize(Decimal("0.01")))
    return value


def _url_key(url: str) -> str:
    return (url or "").split("?")[0]


def _cell(value, size=120) -> str:
    text = str(value).replace("|", "/").replace("\n", " ")
    return text if len(text) <= size else text[: size - 1] + "…"


def _cat_label(cat) -> str:
    parent = cat.parent if (cat.parent_id or cat._state.adding) else None
    return f"{parent.name} › {cat.name}" if parent else cat.name


def download(url: str, attempts: int = 3, timeout: int = 30) -> bytes:
    """Télécharge une image Shopify (HTTPS cdn.shopify.com seulement), avec nouvelles tentatives."""
    if not url.startswith(IMAGE_HOST):
        raise ValueError("adresse d'image refusée (cdn.shopify.com uniquement)")
    delay, last = 1.0, None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Jodhur-import/2.0"})  # noqa: S310
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (hôte vérifié)
                data = resp.read(settings.MEDIA_MAX_UPLOAD_BYTES + 1)
            if len(data) > settings.MEDIA_MAX_UPLOAD_BYTES:
                raise ValueError("image trop lourde")
            return data
        except ValueError:
            raise
        except OSError as exc:  # réseau, délai, 5xx…
            last = exc
            if attempt < attempts:
                time.sleep(delay)
                delay *= 2
    raise OSError(f"échec après {attempts} tentatives : {last}")


class Command(BaseCommand):
    help = "Import complet des produits actifs Shopify (aperçu par défaut ; --appliquer pour écrire)."

    def add_arguments(self, parser):
        parser.add_argument("--appliquer", action="store_true", help="Écrit en base. Sans cette option : aperçu.")
        parser.add_argument("--dry-run", action="store_true", help="Aperçu (comportement par défaut).")
        parser.add_argument("--source", default=str(DEFAULTS["source"]), help="Fichier JSON, ou « shopify » (API).")
        parser.add_argument("--export", help="Avec --source shopify : enregistre l'export lu dans ce fichier.")
        parser.add_argument("--page", type=int, default=10, help="Produits par page (API).")
        parser.add_argument("--report", help="Rapport Markdown.")
        parser.add_argument("--csv", help="Détail produit par produit (CSV).")
        parser.add_argument("--sans-images", action="store_true", help="Ne télécharge aucune image (essais).")
        parser.add_argument("--correspondances", default=str(DEFAULTS["correspondances"]))
        parser.add_argument("--nouvelles-categories", default=str(DEFAULTS["nouvelles_categories"]))
        parser.add_argument("--categories-produits", default=str(DEFAULTS["categories_produits"]))
        parser.add_argument("--base-precedente", default=str(DEFAULTS["base_precedente"]),
                            help="Export du premier import (référence des valeurs déjà importées).")  # fmt: skip
        parser.add_argument("--modele-correspondances", help="Écrit le tableau de correspondances à remplir.")
        parser.add_argument(
            "--rendre-visibles",
            default="",
            help="« utiles » : rend visibles, AVANT l'activation des produits, les catégories proposées"
            " (fichier des nouvelles catégories) qui contiendront au moins un produit actif ; ou une liste"
            " d'identifiants URL séparés par des virgules. Vide : aucune catégorie n'est rendue visible.",
        )

    # --- Entrée -------------------------------------------------------------------------------------
    def handle(self, *args, **opts):
        if opts["appliquer"] and opts["dry_run"]:
            raise CommandError("--appliquer et --dry-run sont incompatibles.")
        self.apply = opts["appliquer"]
        self.with_images = not opts["sans_images"]
        doc, nodes = self._read_source(opts)
        if any(n.get("status") != "ACTIVE" for n in nodes):
            raise CommandError("La source contient des produits non actifs : refusée.")
        products = [src.normalize(n) for n in nodes]
        if not products:
            raise CommandError("Aucun produit actif dans la source.")
        self.previous = self._load_previous(opts["base_precedente"])

        by_name = {}
        for c in Collection.objects.all():
            by_name.setdefault(_norm(c.name), []).append(c)
        self.collections = by_name
        self.new_categories, self.new_categories_report = [], []
        if opts["nouvelles_categories"] and Path(opts["nouvelles_categories"]).is_file():
            self.new_categories = self._load_new_categories(Path(opts["nouvelles_categories"]))
        cats = {}
        for c in [*Category.objects.select_related("parent"), *self.new_categories]:
            cats.setdefault(_norm(c.name), []).append(c)
        self.categories = cats
        self.by_slug = {c.slug: c for c in [*Category.objects.select_related("parent"), *self.new_categories]}
        if opts["modele_correspondances"]:
            self._write_mapping_template(Path(opts["modele_correspondances"]), products)
            return
        self.mapping, self.mapping_path = {}, ""
        if opts["correspondances"] and Path(opts["correspondances"]).is_file():
            self.mapping = self._load_mapping(Path(opts["correspondances"]), products)
            self.mapping_path = opts["correspondances"]
        self.per_product, self.per_product_skipped = {}, 0
        if opts["categories_produits"] and Path(opts["categories_produits"]).is_file():
            self.per_product = self._load_per_product(Path(opts["categories_produits"]), products)

        rows = [self._plan(p) for p in products]
        self._flag_ambiguities(products, rows)
        self.visible_plan = self._plan_visibility(opts["rendre_visibles"], rows)
        if self.apply:
            self._apply_visibility()  # d'abord les catégories, ensuite l'activation des produits
            for p, row in zip(products, rows, strict=True):
                if row["action"] in (CREATED, UPDATE, LINK):
                    self._apply(p, row)
        report = self._render(doc, products, rows)
        if opts["report"]:
            Path(opts["report"]).write_text(report, encoding="utf-8")
        else:
            self.stdout.write(report)
        if opts["csv"]:
            self._csv(Path(opts["csv"]), rows)
        counts = Counter(r["result"] for r in rows)
        mode = "IMPORT APPLIQUÉ" if self.apply else "APERÇU (aucune écriture)"
        self.stdout.write(f"{mode} — " + ", ".join(f"{k} : {v}" for k, v in sorted(counts.items())))

    def _read_source(self, opts):
        if opts["source"] == "shopify":
            env = os.environ
            try:
                nodes = src.fetch_from_api(
                    env.get("SHOPIFY_STORE_DOMAIN", ""),
                    env.get("SHOPIFY_ADMIN_TOKEN", ""),
                    env.get("SHOPIFY_API_VERSION", "2026-01"),
                    opts["page"],
                    log=self.stdout.write,
                )
            except src.SourceError as exc:
                raise CommandError(str(exc)) from exc
            doc = {"source": "API Shopify (lecture seule)", "shop": env.get("SHOPIFY_STORE_DOMAIN"),
                   "exportedAt": timezone.now().isoformat(), "products": nodes}  # fmt: skip
            if opts["export"]:
                Path(opts["export"]).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            return doc, nodes
        path = Path(opts["source"])
        if not path.exists():
            raise CommandError(f"Fichier introuvable : {path}")
        try:
            return src.load_file(path)
        except src.SourceError as exc:
            raise CommandError(str(exc)) from exc

    def _load_previous(self, path) -> dict:
        """Premier export (format simple) : valeurs que le premier import a écrites, par identifiant Shopify."""
        if not path or not Path(path).is_file():
            return {}
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        out = {}
        for p in doc.get("products") or []:
            if "variants" not in p or "images" not in p:
                continue
            out[p["id"]] = {
                "fields": {
                    "name": p["title"][:200],
                    "display_name": p["title"][:255],
                    "summary": src.first_paragraph(p.get("descriptionHtml")),
                    "description_html": sanitize_html(p.get("descriptionHtml") or ""),
                    "supplier": (p.get("vendor") or "")[:150],
                },
                "variants": {
                    v["id"]: {
                        "price": str(Decimal(v["price"]).quantize(Decimal("0.01"))),
                        "stock_quantity": v.get("inventoryQuantity") if v.get("tracked") else None,
                    }
                    for v in p["variants"]
                },
                "image_urls": [_url_key(i["url"]) for i in p["images"]],
                "handle": p["handle"],
            }
        return out

    # --- Valeurs voulues (Shopify → champs Jodhur) ---------------------------------------------------
    def _desired(self, p: dict) -> tuple[dict, list[str]]:
        notes = []
        mf = {f"{m['namespace']}.{m['key']}": m for m in p["metafields"]}
        desc = p["descriptionHtml"]
        want = {
            "name": p["title"][:200],
            "display_name": p["title"][:255],
            "brand": p["vendor"][:100],
            "supplier": p["vendor"][:150],
            "summary": src.first_paragraph(desc),
            "description_html": sanitize_html(desc),
        }
        for key, (field, kind) in METAFIELD_FIELDS.items():
            if key not in mf:
                continue
            lines = src.rich_text_lines(mf[key]["value"])
            if kind == "lines":
                want[field] = lines
            elif kind == "bullets":
                want[field] = src.bullet_free(lines)
            elif kind == "text255":
                want[field] = " ".join(lines)[:255]
            elif kind == "text160":
                text = " ".join(lines)
                if len(text) <= 160:
                    want[field] = text
                else:
                    notes.append("phrase courte (custom.description_courte) non reprise : plus de 160 caractères")
        title, cut_t = src.cut(p["seoTitle"], 70)
        description, cut_d = src.cut(p["seoDescription"], 160)
        want["seo_title"], want["seo_description"] = title, description
        if cut_t:
            notes.append("titre SEO coupé à 70 caractères (texte complet gardé dans Shopify)")
        if cut_d:
            notes.append("méta-description coupée à 160 caractères (plus longue dans Shopify)")
        return want, notes

    def _desired_variant(self, v: dict) -> dict:
        price = Decimal(v["price"])
        compare = Decimal(v["compareAtPrice"]) if v.get("compareAtPrice") else None
        return {
            "title": v["title"][:160],
            "sku": v["sku"] or None,
            "barcode": v["barcode"] or None,
            "price": price,
            "compare_at_price": compare if compare and compare > price else None,
            "stock_quantity": v["inventoryQuantity"] if v["tracked"] else None,
            "track_inventory": v["tracked"],
            "allow_backorder": v["backorder"],
            "weight_grams": v["weightGrams"],
        }

    @staticmethod
    def _merge(current, wanted, has_base: bool, base):
        """
        Fusion à trois : « set » (remplacer), « same » (déjà égal), « keep » (modifié dans Jodhur : gardé).
        Remplacer seulement si la valeur locale est vide ou égale à la dernière valeur importée.
        """
        cur, new = _json(current), _json(wanted)
        if cur == new:
            return "same"
        if _empty(cur):
            return "set" if not _empty(new) else "same"
        if _empty(new):
            return "same"  # Shopify vide : on n'efface jamais une donnée Jodhur
        if has_base and cur == _json(base):
            return "set"
        return "keep"

    # --- Plan (lecture seule) ------------------------------------------------------------------------
    def _plan(self, p: dict) -> dict:
        row = {
            "p": p,
            "title": p["title"],
            "handle": p["handle"],
            "vendor": p["vendor"],
            "action": CREATED,
            "result": "",
            "changes": [],
            "kept": [],
            "notes": [],
            "images": {"download": [], "link": [], "same": [], "alt_fallback": 0},
            "variants": {"create": [], "update": [], "missing_local": []},
            "categories_add": [],
            "category_values": self._match_categories(p),
            "collection_matches": self._match_collections(p),
            "collections_add": [],
            "local": "",
            "status_before": "",
            "status_after": "",
            "blocked": [],
        }
        row["want"], notes = self._desired(p)
        row["notes"] += notes
        if p["truncated"]:
            row["notes"].append("listes Shopify tronquées à 100 : " + ", ".join(p["truncated"]))
        product = Product.objects.filter(shopify_id=p["id"]).first()
        if product is None:
            candidates = list(
                Product.objects.filter(slug=p["handle"])
                | Product.objects.filter(name__iexact=p["title"])
                | Product.objects.filter(display_name__iexact=p["title"])
            )
            if candidates:
                row["local"] = ", ".join(c.slug for c in candidates)
                if len(candidates) == 1 and not candidates[0].shopify_id:
                    product = candidates[0]
                    row["action"] = LINK
                else:
                    row["action"] = DUP
                    row["ambiguity"] = (
                        "déjà relié à un autre produit Shopify" if len(candidates) == 1 else "plusieurs produits locaux"
                    )
                    row["result"] = DUP
                    return row
        if product is None:
            self._plan_new(p, row)
        else:
            if row["action"] != LINK:
                row["action"] = UPDATE
            self._plan_existing(p, row, product)
        return row

    def _plan_new(self, p, row):
        row["changes"].append("création")
        row["images"]["download"] = list(p["images"]) if self.with_images else []
        row["images"]["alt_fallback"] = sum(1 for i in p["images"] if not i["alt"])
        row["variants"]["create"] = list(p["variants"])
        row["categories_add"] = self._clear_categories(row["category_values"])
        row["collections_add"] = [
            c
            for _n, c in row["collection_matches"]
            if isinstance(c, Collection) and not c.entry_errors(origin="", ingredients=[])
        ]
        row["slug"] = unique_slug(p["handle"], Product) if p["handle"] else unique_slug(p["title"], Product)
        if row["slug"] != p["handle"]:
            row["notes"].append(f"identifiant URL « {row['slug']} » (le handle « {p['handle']} » est déjà pris)")
        row["status_before"] = "—"
        row["blocked"] = self._predict_blockers(row, None)
        row["status_after"] = "actif" if not row["blocked"] else "brouillon"
        row["result"] = "créé actif" if not row["blocked"] else "créé brouillon (bloqué)"
        cats = row["categories_add"]
        if (
            cats
            and not row["blocked"]
            and not any(c.pk and c.is_active and (c.parent is None or c.parent.is_active) for c in cats)
        ):
            row["notes"].append("visible dans « Tous les produits » mais pas dans le menu (catégories masquées)")

    def _plan_existing(self, p, row, product):
        row["product"] = product
        row["local"] = product.slug
        history = self._history(product)
        prev = self.previous.get(p["id"], {})
        base = dict(product.shopify_baseline or {})
        base_fields = base.get("fields") or {}
        if not base_fields and prev and row["action"] == UPDATE:
            base_fields = prev["fields"]
        row["field_ops"] = {}
        for field in PRODUCT_FIELDS:
            if field not in row["want"]:
                continue
            current = getattr(product, field)
            op = self._merge(current, row["want"][field], field in base_fields, base_fields.get(field))
            if field in ("brand", "supplier") and op == "set" and _empty(current) and history[field]:
                op = "keep_cleared"
            row["field_ops"][field] = op
            if op == "set":
                row["changes"].append(FIELD_LABELS[field])
            elif op == "keep":
                row["kept"].append(f"{FIELD_LABELS[field]} modifié(e) dans Jodhur : gardé(e)")
            elif op == "keep_cleared":
                row["kept"].append(f"{FIELD_LABELS[field]} effacé(e) à la main : laissé(e) vide")
        if product.slug != p["handle"]:
            row["notes"].append(f"identifiant URL Jodhur « {product.slug} » ≠ handle Shopify « {p['handle']} » (gardé)")
        # Variantes
        local_variants = list(product.variants.all())
        by_id = {v.shopify_id: v for v in local_variants if v.shopify_id}
        if not by_id and len(local_variants) == 1 and len(p["variants"]) == 1:
            by_id = {p["variants"][0]["id"]: local_variants[0]}
            row["notes"].append("variante unique reliée à la variante Shopify")
        vbase_all = {}
        for v in p["variants"]:
            local = by_id.get(v["id"])
            if local is None:
                row["variants"]["create"].append(v)
                continue
            vbase = dict((local.shopify_baseline or {}).get("fields") or {})
            if not vbase and prev:
                vbase = (prev.get("variants") or {}).get(v["id"], {})
            vbase_all[v["id"]] = vbase
            ops = {}
            for field, wanted in self._desired_variant(v).items():
                op = self._merge(getattr(local, field), wanted, field in vbase, vbase.get(field))
                if field in ("sku", "barcode") and op == "set" and wanted:
                    clash = Variant.objects.filter(**{field: wanted}).exclude(pk=local.pk).exists()
                    if clash:
                        op = "clash"
                ops[field] = op
                label = FIELD_LABELS[field]
                if op == "set":
                    row["changes"].append(f"variante {v['title'] or 'unique'} : {label}")
                elif op == "keep":
                    row["kept"].append(f"variante {v['title'] or 'unique'} : {label} modifié(e) dans Jodhur")
                elif op == "clash":
                    row["kept"].append(f"variante {v['title'] or 'unique'} : {label} « {wanted} » déjà utilisé")
            row["variants"]["update"].append((v, local, ops))
        known = {v["id"] for v in p["variants"]}
        row["variants"]["missing_local"] = [v for v in local_variants if v.shopify_id and v.shopify_id not in known]
        if row["variants"]["missing_local"]:
            row["notes"].append(f"{len(row['variants']['missing_local'])} variante(s) absente(s) de Shopify (gardées)")
        if row["variants"]["create"] and product.options.exists() is False and len(p["variants"]) > 1:
            row["notes"].append("nouvelles variantes Shopify sur un produit sans options : à ajouter à la main")
            row["variants"]["create"] = []
        # Images
        self._plan_images(p, row, product, prev)
        # Catégories (ajout seulement ; catégories choisies à la main protégées)
        self._plan_categories(row, product, history)
        current_colls = set(product.collections.values_list("pk", flat=True))
        for _n, coll in row["collection_matches"]:
            if not isinstance(coll, Collection) or coll.pk in current_colls or coll in row["collections_add"]:
                continue
            if coll.pk in history["collections"]:
                row["kept"].append(f"collection « {coll.name} » retirée à la main : non remise")
            elif coll.entry_errors(origin=product.origin_country, ingredients=product.ingredients):
                row["kept"].append(f"collection « {coll.name} » : règle d'entrée non remplie")
            else:
                row["collections_add"].append(coll)
                row["changes"].append(f"collection + {coll.name}")
        # Statut
        row["status_before"] = product.get_status_display()
        row["blocked"] = self._predict_blockers(row, product)
        if product.status == Product.Status.ACTIVE:
            row["status_after"] = "actif"
            if row["blocked"]:
                row["notes"].append("actif dans Jodhur mais incomplet : " + "; ".join(row["blocked"]))
        elif product.status == Product.Status.ARCHIVED:
            row["status_after"] = "archivé (gardé)"
            row["kept"].append("archivé dans Jodhur : statut gardé")
        elif history["manual_status"]:
            row["status_after"] = "brouillon (gardé)"
            row["kept"].append("mis en brouillon à la main dans Jodhur : statut gardé")
        else:
            row["status_after"] = "actif" if not row["blocked"] else "brouillon"
            if not row["blocked"]:
                row["changes"].append("statut → actif")
        vis = self._masked_categories(product, row)
        if vis and row["status_after"] == "actif":
            row["notes"].append("visible dans « Tous les produits » mais pas dans le menu (catégories masquées)")
        done = row["action"] if row["changes"] else "déjà à jour"
        row["result"] = (
            f"{done} — bloqué (brouillon)" if row["status_after"] == "brouillon" and row["blocked"] else done
        )
        row["vbase"] = vbase_all

    def _plan_images(self, p, row, product, prev):
        existing = list(product.images.select_related("media"))
        by_media = {pi.shopify_media_id: pi for pi in existing if pi.shopify_media_id}
        # Images du premier import (sans identifiant Shopify) : retrouvées par leur rang dans le premier export.
        old_by_url = {}
        if prev:
            pattern = re.compile(rf"^shopify-{re.escape(prev['handle'])}-(\d+)\.")
            for pi in existing:
                if pi.shopify_media_id:
                    continue
                match = pattern.match(pi.media.original_filename or "")
                if match and int(match.group(1)) <= len(prev["image_urls"]):
                    old_by_url[prev["image_urls"][int(match.group(1)) - 1]] = pi
        base_alts = ((product.shopify_baseline or {}).get("images") or {}) if product else {}
        for img in p["images"]:
            pi = by_media.get(img["id"]) or old_by_url.get(_url_key(img["url"]))
            alt = (img["alt"] or p["title"])[:255]
            if not img["alt"]:
                row["images"]["alt_fallback"] += 1
            if pi is None:
                if self.with_images:
                    row["images"]["download"].append(img)
                continue
            op = self._merge(pi.alt, alt, img["id"] in base_alts, base_alts.get(img["id"]))
            row["images"]["link" if not pi.shopify_media_id else "same"].append((img, pi, op))
            if op == "keep":
                row["kept"].append("texte alternatif d'une image modifié dans Jodhur : gardé")
        n_dl, n_link = len(row["images"]["download"]), sum(1 for x in row["images"]["link"])
        if n_dl:
            row["changes"].append(f"{n_dl} image(s) à télécharger")
        if n_link:
            row["changes"].append(f"{n_link} image(s) existante(s) reliée(s) à Shopify")
        removed = [
            pi for pi in existing if pi.shopify_media_id and pi.shopify_media_id not in {i["id"] for i in p["images"]}
        ]
        if removed:
            row["notes"].append(f"{len(removed)} image(s) absente(s) de Shopify (gardées)")

    def _plan_categories(self, row, product, history):
        clear = self._clear_categories(row["category_values"])
        links = list(ProductCategory.objects.filter(product=product).select_related("category__parent"))
        current = [link.category for link in links]
        by_import = set(history["categories"])
        if history["created"]:
            by_import |= {c.pk for c in self._exact_categories(row["p"])}
        manual = [c for c in current if c.pk not in by_import]
        missing = [c for c in clear if c not in current]
        if manual:
            if missing:
                row["kept"].append(
                    "catégorie(s) choisie(s) à la main : rien n'est ajouté (proposé : "
                    + ", ".join(_cat_label(c) for c in missing)
                    + ")"
                )
            return
        for c in missing:
            if c.pk and c.pk in history["categories"]:
                row["kept"].append(f"catégorie « {_cat_label(c)} » retirée à la main : non remise")
                continue
            row["categories_add"].append(c)
            row["changes"].append(f"catégorie + {_cat_label(c)}{' (nouvelle)' if not c.pk else ''}")

    def _masked_categories(self, product, row) -> bool:
        cats = [
            link.category for link in ProductCategory.objects.filter(product=product).select_related("category__parent")
        ]
        cats += row["categories_add"]
        if not cats:
            return False
        return not any(c.pk and c.is_active and (c.parent is None or c.parent.is_active) for c in cats)

    def _predict_blockers(self, row, product) -> list[str]:
        """Conditions d'activation (mêmes règles que l'admin), évaluées sur l'état APRÈS import."""
        want, ops = row["want"], row.get("field_ops", {})

        def final(field):
            if product is None:
                return want.get(field)
            return want[field] if ops.get(field) == "set" else getattr(product, field)

        errors = []
        if _empty((final("brand") or "").strip()):
            errors.append("La marque est obligatoire." + (" (Vendor vide dans Shopify)" if not row["vendor"] else ""))
        if _empty((final("name") or "").strip()):
            errors.append("Le nom est obligatoire.")
        if _empty((final("summary") or "").strip()):
            errors.append("La description est obligatoire. (description Shopify vide)")
        has_cat = bool(row["categories_add"]) or (product is not None and product.category_links.exists())
        if not has_cat:
            values = ", ".join(n for n, _c, _s in row["category_values"]) or "aucune valeur Shopify"
            errors.append(f"Au moins une catégorie est obligatoire. (aucune correspondance pour : {values})")
        n_images = len(row["images"]["download"]) + len(row["images"]["link"]) + len(row["images"]["same"])
        if product is not None:
            n_images = max(n_images, product.images.filter(in_gallery=True).count())
        if not n_images:
            errors.append(
                "Au moins une image dans la galerie est obligatoire." + ("" if self.with_images else " (--sans-images)")
            )
        variants = row["p"]["variants"]
        if not variants and (product is None or not product.variants.exists()):
            errors.append("Une variante par défaut est obligatoire.")
        elif variants and Decimal(variants[0]["price"]) <= 0:
            errors.append("Le prix doit être supérieur à 0.")
        return errors

    # --- Historique (retraits / modifications manuels) -----------------------------------------------
    def _history(self, product) -> dict:
        logs = AuditLog.objects.filter(target_type="catalog.product", target_id=str(product.pk))
        out = {"supplier": False, "brand": False, "collections": set(), "categories": set(), "created": False,
               "manual_status": False}  # fmt: skip
        for log in logs:
            ch = log.changes or {}
            if log.action in (ACTION_CREATE, ACTION_UPDATE):
                out["created"] = out["created"] or log.action == ACTION_CREATE
                out["supplier"] = out["supplier"] or bool(ch.get("supplier"))
                out["brand"] = out["brand"] or bool(ch.get("brand"))
                out["collections"].update(ch.get("collectionsAdded") or [])
                out["categories"].update(ch.get("categoriesAdded") or [])
            elif log.action == "product.status" and log.actor_id is not None:
                out["manual_status"] = True
        return out

    # --- Catégories et collections (correspondances explicites) --------------------------------------
    def _values(self, p):
        values = [(c, c) for c in p["collections"]]
        if p["category"]:
            values.append((p["category"], p["category"].split(">")[-1].strip()))
        return values

    def _match_categories(self, p) -> list:
        out = []
        for name, exact in self._values(p):
            chosen = self.mapping.get(_norm(name))
            if chosen is not None:
                cats, statut = chosen
                src_label = "tableau" + (f" · {statut}" if statut else "")
                out += [(name, c, src_label) for c in cats] or [(name, None, src_label)]
                continue
            found = self.categories.get(_norm(exact)) or []
            out.append((name, found[0] if len(found) == 1 else ("ambigu" if found else None), "nom identique"))
        for cat in self.per_product.get(p["handle"], []):
            out.append((f"liste produit : {p['title']}", cat, "liste produit · validé"))
        return out

    @staticmethod
    def _clear_categories(matches) -> list:
        found = []
        for _n, cat, _s in matches:
            if isinstance(cat, Category) and cat not in found:
                found.append(cat)
        return found

    def _exact_categories(self, p) -> list:
        found = []
        for _name, exact in self._values(p):
            cats = [c for c in self.categories.get(_norm(exact)) or [] if c.pk]
            if len(cats) == 1 and cats[0] not in found:
                found.append(cats[0])
        return found

    def _match_collections(self, p) -> list:
        out = []
        for name in p["collections"]:
            found = self.collections.get(_norm(name)) or []
            out.append((name, found[0] if len(found) == 1 else ("ambigu" if found else None)))
        return out

    def _load_mapping(self, path: Path, products) -> dict:
        known = {_norm(n) for p in products for n, _e in self._values(p)}
        mapping, errors, seen = {}, [], set()
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for i, line in enumerate(csv.DictReader(fh, delimiter=";"), start=2):
                name = (line.get("collection_shopify") or "").strip()
                value = (line.get("categorie_jodhur") or "").strip()
                statut = (line.get("statut") or "").strip()
                if not name:
                    continue
                key = _norm(name)
                if key in seen:
                    errors.append(f"ligne {i} : « {name} » figure deux fois")
                    continue
                seen.add(key)
                if key not in known:
                    continue  # valeur qui n'existe plus dans Shopify : ignorée
                if not value:
                    continue
                if _norm(value) == "aucune":
                    mapping[key] = ([], statut)
                    continue
                cats = []
                for slug in (v.strip() for v in value.split("|") if v.strip()):
                    if slug not in self.by_slug:
                        errors.append(f"ligne {i} : catégorie Jodhur « {slug} » inconnue")
                    elif self.by_slug[slug] not in cats:
                        cats.append(self.by_slug[slug])
                mapping[key] = (cats, statut)
        if errors:
            raise CommandError("Tableau de correspondances refusé, rien n'a été fait :\n- " + "\n- ".join(errors))
        self.mapping_rows = seen
        return mapping

    def _load_per_product(self, path: Path, products) -> dict:
        handles = {p["handle"] for p in products}
        out, errors = {}, []
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for i, line in enumerate(csv.DictReader(fh, delimiter=";"), start=2):
                handle = (line.get("handle") or "").strip()
                if not handle or handle not in handles:
                    continue
                if _norm(line.get("appliquer") or "") != "oui":
                    self.per_product_skipped += 1
                    continue
                cats = []
                for slug in (v.strip() for v in (line.get("categorie_jodhur") or "").split("|") if v.strip()):
                    if slug not in self.by_slug:
                        errors.append(f"ligne {i} : catégorie Jodhur « {slug} » inconnue")
                    elif self.by_slug[slug] not in cats:
                        cats.append(self.by_slug[slug])
                out[handle] = cats
        if errors:
            raise CommandError("Liste produit par produit refusée, rien n'a été fait :\n- " + "\n- ".join(errors))
        return out

    def _load_new_categories(self, path: Path) -> list:
        existing = {c.slug: c for c in Category.objects.select_related("parent")}
        rows = []
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for i, line in enumerate(csv.DictReader(fh, delimiter=";"), start=2):
                slug, name = (line.get("identifiant_url") or "").strip(), (line.get("nom") or "").strip()
                if not slug and not name:
                    continue
                if not slug or not name or slugify(slug) != slug:
                    raise CommandError(f"Nouvelles catégories, ligne {i} : identifiant URL et nom obligatoires.")
                rows.append(
                    (slug, name[:100], (line.get("nom_ar") or "").strip()[:100], (line.get("parente") or "").strip())
                )
        new = []
        with transaction.atomic():
            for slug, name, name_ar, parent_slug in rows:
                if slug in existing:
                    self.new_categories_report.append((existing[slug], "existe déjà"))
                    continue
                parent = existing.get(parent_slug) if parent_slug else None
                if parent_slug and parent is None:
                    raise CommandError(f"Catégorie parente « {parent_slug} » introuvable pour « {slug} ».")
                cat = Category(slug=slug, name=name, name_ar=name_ar, parent=parent, is_active=False, position=900)
                if self.apply:
                    cat.save()
                    log_action("category.import_shopify", target=cat, changes={"slug": slug, "name": name})
                self.new_categories_report.append((cat, "créée masquée" if self.apply else "à créer (masquée)"))
                existing[slug] = cat
                new.append(cat)
        return new

    def _write_mapping_template(self, path: Path, products):
        counts, kinds, examples = Counter(), {}, {}
        for p in products:
            vals = [(c, "collection") for c in p["collections"]] + (
                [(p["category"], "catégorie Shopify")] if p["category"] else []
            )
            for v, k in dict.fromkeys(vals):
                counts[v] += 1
                kinds[v] = k
                examples.setdefault(v, []).append(p["title"])
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(MAPPING_HEADER)
            for name, n in counts.most_common():
                same = self.categories.get(_norm(name.split(">")[-1])) or []
                w.writerow(
                    [
                        name,
                        kinds[name],
                        n,
                        " | ".join(examples[name][:3]),
                        same[0].slug if len(same) == 1 else "",
                        "",
                        "",
                        "",
                    ]
                )
        self.stdout.write(f"Tableau à remplir : {path} ({len(counts)} valeurs). Aucune écriture en base.")

    def _flag_ambiguities(self, products, rows):
        titles = Counter(p["title"].strip().lower() for p in products)
        claims = Counter(r["product"].pk for r in rows if r["action"] == LINK)
        for p, row in zip(products, rows, strict=True):
            if titles[p["title"].strip().lower()] > 1:
                row["notes"].append(
                    f"même nom que {titles[p['title'].strip().lower()] - 1} autre(s) produit(s) Shopify"
                )
            if row["action"] == LINK and (titles[p["title"].strip().lower()] > 1 or claims[row["product"].pk] > 1):
                row["action"] = row["result"] = DUP
                row["ambiguity"] = "plusieurs produits Shopify correspondent au même produit local"
        groups = {}
        for v in {p["vendor"] for p in products}:
            groups.setdefault(_supplier_key(v), set()).add(v)
        self.supplier_groups = [sorted(g) for g in groups.values() if len(g) > 1]

    # --- Application ---------------------------------------------------------------------------------
    def _apply(self, p, row):
        assets = self._download_images(row)
        try:
            with transaction.atomic():
                create = row["action"] == CREATED
                product = self._create(p, row, assets) if create else self._update(p, row, assets)
        except Exception as exc:  # noqa: BLE001 — un produit en échec n'arrête pas l'import
            row["result"] = "échec"
            row["status_after"] = "—"
            row["notes"].append(f"erreur : {exc}")
            return
        row["product"] = product
        self._finish_status(product, row)

    def _download_images(self, row) -> dict:
        assets, failures = {}, []
        for img in row["images"]["download"]:
            try:
                data = download(img["url"])
                name = f"shopify-{row['handle']}-{img['position'] + 1}.img"
                asset, _created = create_from_upload(
                    ContentFile(data, name=name), alt=(img["alt"] or row["title"])[:255]
                )
                assets[img["id"]] = asset
            except (OSError, ValueError, ImageRejected) as exc:
                failures.append(f"image {img['position'] + 1} non importée ({exc})")
        row["notes"] += failures
        row["images"]["failed"] = len(failures)
        return assets

    def _attach_images(self, product, p, row, assets) -> dict:
        """Images téléchargées → galerie (sans doublon : même fichier déjà présent = relié, pas recopié)."""
        start = (product.images.aggregate(m=Max("position"))["m"] or -1) + 1
        by_media_id = {}
        for img in p["images"]:
            asset = assets.get(img["id"])
            if asset is None:
                continue
            alt = (img["alt"] or p["title"])[:255]
            pi = ProductImage.objects.filter(product=product, media=asset).first()
            if pi is not None:
                pi.shopify_media_id = img["id"]
                pi.save(update_fields=["shopify_media_id"])
            else:
                pi = ProductImage.objects.create(product=product, media=asset, alt=alt, position=start,
                                                 in_gallery=True, shopify_media_id=img["id"])  # fmt: skip
                start += 1
            by_media_id[img["id"]] = pi
        for img, pi, op in row["images"]["link"] + row["images"]["same"]:
            fields = []
            if not pi.shopify_media_id:
                pi.shopify_media_id = img["id"]
                fields.append("shopify_media_id")
            if op == "set":
                pi.alt = (img["alt"] or p["title"])[:255]
                fields.append("alt")
            if fields:
                pi.save(update_fields=fields)
            by_media_id[img["id"]] = pi
        return by_media_id

    def _set_categories(self, product, cats):
        start = (ProductCategory.objects.filter(product=product).aggregate(m=Max("position"))["m"] or -1) + 1
        saved = []
        for i, cat in enumerate(cats):
            if not cat.pk:  # nouvelle catégorie : créée au chargement en mode application
                cat = Category.objects.get(slug=cat.slug)
            ProductCategory.objects.get_or_create(product=product, category=cat, defaults={"position": start + i})
            saved.append(cat.pk)
        return saved

    def _mirror(self, product, p):
        product.shopify_handle = p["handle"][:255]
        product.shopify_product_type = p["productType"][:255]
        product.shopify_category = p["category"][:255]
        product.shopify_tags = p["tags"]
        product.shopify_collections = p["collections"]
        product.shopify_updated_at = parse_datetime(p["updatedAt"]) if p["updatedAt"] else None
        product.shopify_synced_at = timezone.now()

    def _sync_metafields(self, product, p):
        seen = set()
        for m in p["metafields"]:
            ProductMetafield.objects.update_or_create(
                product=product, namespace=m["namespace"][:100], key=m["key"][:100],
                defaults={"shopify_id": m["id"], "type": m["type"][:80], "value": m["value"], "in_shopify": True},
            )  # fmt: skip
            seen.add((m["namespace"][:100], m["key"][:100]))
        for mf in ProductMetafield.objects.filter(product=product, in_shopify=True):
            if (mf.namespace, mf.key) not in seen:
                mf.in_shopify = False
                mf.save(update_fields=["in_shopify", "updated_at"])

    def _create(self, p, row, assets) -> Product:
        want = row["want"]
        product = Product(
            slug=unique_slug(p["handle"] or p["title"], Product),
            position=(Product.objects.aggregate(m=Max("position"))["m"] or 0) + 1,
            shopify_id=p["id"],
            status=Product.Status.DRAFT,
            **{f: want[f] for f in PRODUCT_FIELDS if f in want},
        )
        self._mirror(product, p)
        product.shopify_baseline = {"fields": {f: _json(want[f]) for f in PRODUCT_FIELDS if f in want}}
        product.save()
        images = self._attach_images(product, p, row, assets)
        product.shopify_baseline["images"] = {img["id"]: (img["alt"] or p["title"])[:255] for img in p["images"]}
        product.save(update_fields=["shopify_baseline"])
        cats = self._set_categories(product, row["categories_add"])
        product.collections.add(*row["collections_add"])
        self._sync_metafields(product, p)
        self._create_variants(product, p, p["variants"], images, fresh=True)
        log_action(ACTION_CREATE, target=product, changes={
            "shopifyId": p["id"], "supplier": product.supplier, "brand": product.brand,
            "variants": len(p["variants"]), "images": len(images),
            "collectionsAdded": [c.pk for c in row["collections_add"]], "categoriesAdded": cats,
        })  # fmt: skip
        return product

    def _create_variants(self, product, p, variants, images, fresh):
        options = p["options"]
        values = {}
        multi = len(p["variants"]) > 1
        if multi and fresh:
            for oi, opt in enumerate(options):
                option = ProductOption.objects.create(
                    product=product, name=OPTION_NAMES.get(opt["name"], opt["name"])[:50], position=oi
                )
                for vi, value in enumerate(opt["values"]):
                    values[(opt["name"], value)] = ProductOptionValue.objects.create(
                        option=option, value=value[:50], position=vi
                    )
        elif multi:
            for option in product.options.prefetch_related("values"):
                for ov in option.values.all():
                    values[(option.name, ov.value)] = ov
                    for raw, shown in OPTION_NAMES.items():
                        if shown == option.name:
                            values[(raw, ov.value)] = ov
        has_default = product.variants.filter(is_default=True).exists()
        start = (product.variants.aggregate(m=Max("position"))["m"] or -1) + 1
        for i, v in enumerate(variants):
            data = self._desired_variant(v)
            for field in ("sku", "barcode"):
                if data[field] and Variant.objects.filter(**{field: data[field]}).exists():
                    data[field] = None
            variant = Variant.objects.create(
                product=product, shopify_id=v["id"], position=start + i,
                is_default=not has_default and i == 0, image=images.get(v["mediaId"]),
                shopify_baseline={"fields": {k: _json(val) for k, val in data.items()}}, **data,
            )  # fmt: skip
            if multi:
                VariantOptionValue.objects.bulk_create([
                    VariantOptionValue(variant=variant, option_value=values[(o["name"], o["value"])])
                    for o in v["options"] if (o["name"], o["value"]) in values
                ])  # fmt: skip
            if data["stock_quantity"] is not None:
                StockMovement.objects.create(variant=variant, delta=data["stock_quantity"], quantity_before=None,
                                             quantity_after=data["stock_quantity"],
                                             reason=StockMovement.Reason.INITIAL_COUNT, note=NOTE)  # fmt: skip

    def _update(self, p, row, assets) -> Product:
        product = Product.objects.select_for_update().get(pk=row["product"].pk)
        want = row["want"]
        base = dict(product.shopify_baseline or {})
        base_fields = dict(base.get("fields") or {})
        fields = []
        if row["action"] == LINK:
            if Product.objects.filter(shopify_id=p["id"]).exclude(pk=product.pk).exists():
                raise ValueError("identifiant Shopify déjà utilisé")
            product.shopify_id = p["id"]
            fields.append("shopify_id")
        changed = {}
        for field, op in row["field_ops"].items():
            if op == "set":
                setattr(product, field, want[field])
                fields.append(field)
                changed[field] = True
            if op in ("set", "same"):
                base_fields[field] = _json(want[field])
        self._mirror(product, p)
        images = self._attach_images(product, p, row, assets)
        base_imgs = dict(base.get("images") or {})
        for img in p["images"]:
            if img["id"] in images:
                base_imgs[img["id"]] = (img["alt"] or p["title"])[:255]
        product.shopify_baseline = {**base, "fields": base_fields, "images": base_imgs}
        product.save()
        # Variantes
        for v, local, ops in row["variants"]["update"]:
            local = Variant.objects.select_for_update().get(pk=local.pk)
            data = self._desired_variant(v)
            vbase = dict((local.shopify_baseline or {}).get("fields") or row["vbase"].get(v["id"]) or {})
            before_stock = local.stock_quantity
            vfields = []
            if not local.shopify_id:
                local.shopify_id = v["id"]
                vfields.append("shopify_id")
            for field, op in ops.items():
                if op == "set":
                    setattr(local, field, data[field])
                    vfields.append(field)
                if op in ("set", "same"):
                    vbase[field] = _json(data[field])
            if local.compare_at_price is not None and local.compare_at_price <= local.price:
                local.compare_at_price = None  # contrainte « prix barré > prix »
                vfields.append("compare_at_price")
            if v["mediaId"] in images and local.image_id is None:
                local.image = images[v["mediaId"]]
                vfields.append("image")
            local.shopify_baseline = {"fields": vbase}
            local.save()
            if "stock_quantity" in vfields and local.stock_quantity is not None:
                StockMovement.objects.create(
                    variant=local, delta=local.stock_quantity - (before_stock or 0), quantity_before=before_stock,
                    quantity_after=local.stock_quantity, reason=StockMovement.Reason.RECOUNT, note=NOTE,
                )  # fmt: skip
        if row["variants"]["create"]:
            self._create_variants(product, p, row["variants"]["create"], images, fresh=False)
        cats = self._set_categories(product, row["categories_add"])
        product.collections.add(*row["collections_add"])
        self._sync_metafields(product, p)
        log_action(ACTION_UPDATE, target=product, changes={
            "shopifyId": p["id"], "linked": row["action"] == LINK, "fields": sorted(changed),
            "supplier": want["supplier"] if changed.get("supplier") else "",
            "brand": want["brand"] if changed.get("brand") else "",
            "collectionsAdded": [c.pk for c in row["collections_add"]], "categoriesAdded": cats,
        })  # fmt: skip
        return product

    def _finish_status(self, product, row):
        """Active le produit s'il le peut ; sinon le laisse en brouillon et note précisément ce qui manque."""
        product.refresh_from_db()
        predicted = row["blocked"]
        errors = services.activation_errors(product)
        # Message détaillé de l'aperçu (ex. valeurs Shopify sans correspondance) quand il s'agit du même champ.
        row["blocked"] = [next((d for d in predicted if d.startswith(e.rstrip("."))), e) for e in errors]
        if product.status == Product.Status.ACTIVE:
            row["status_after"] = "actif"
            return
        if product.status == Product.Status.ARCHIVED or (
            row["action"] != CREATED and self._history(product)["manual_status"]
        ):
            return
        if errors:
            row["status_after"] = "brouillon"
            done = row["action"] if row["changes"] else "déjà à jour"
            row["result"] = f"{done} — bloqué (brouillon)" if row["action"] != CREATED else "créé brouillon (bloqué)"
            return
        services.change_status(product, Product.Status.ACTIVE)
        row["status_after"] = "actif"
        row["result"] = "créé actif" if row["action"] == CREATED else f"{row['action']} — activé"

    # --- Rapport ------------------------------------------------------------------------------------
    def _render(self, doc, products, rows) -> str:
        counts = Counter(r["result"] for r in rows)
        n_var = sum(len(p["variants"]) for p in products)
        n_img = sum(len(p["images"]) for p in products)
        n_mf = sum(len(p["metafields"]) for p in products)
        title = "IMPORT APPLIQUÉ" if self.apply else "APERÇU (aucune écriture)"
        blocked = [r for r in rows if r["blocked"] and r["status_after"] != "actif" and r["action"] != DUP]
        lines = [
            f"# Import Shopify → Jodhur — {title}",
            "",
            f"Source : {doc.get('source', '?')} · boutique {doc.get('shop', '?')}"
            f" · export du {doc.get('exportedAt', '?')}",
            f"{len(products)} produits actifs · {n_var} variantes · {n_img} images · {n_mf} metafields.",
            "",
            "Résultat : " + " · ".join(f"**{k}** : {v}" for k, v in sorted(counts.items())),
            "",
            "## Statut dans Jodhur",
            "",
            f"- Actifs après import : **{sum(1 for r in rows if r['status_after'] == 'actif')}**",
            f"- Bloqués en brouillon : **{len(blocked)}** (détail ci-dessous)",
            f"- Statut gardé (archivé / mis en brouillon à la main) : "
            f"{sum(1 for r in rows if 'gardé' in r['status_after'])}",
            f"- Actifs dont toutes les catégories sont masquées (absents du menu, présents dans « Tous les produits »)"
            f" : {sum(1 for r in rows if any('catégories masquées' in n for n in r['notes']))}",
            "",
            "### Produits bloqués (champ manquant)",
            "",
        ]
        lines += [f"- **{r['title']}** (`{r['handle']}`) : " + " ".join(r["blocked"]) for r in blocked] or ["- Aucun."]
        lines += self._render_categories(rows)
        lines += self._render_images(rows)
        lines += self._render_conflicts(rows)
        lines += self._render_misc(products, rows)
        lines += self._render_detail(rows)
        return "\n".join(lines) + "\n"

    # --- Catégories rendues visibles avant l'activation ------------------------------------------------
    def _plan_visibility(self, choice: str, rows) -> list:
        """
        Catégories à rendre visibles. « utiles » = catégories du fichier des nouvelles catégories (proposées pour
        Shopify), encore masquées, qui contiendront au moins un produit actif après l'import, + leur parente.
        Les catégories masquées volontairement dans Jodhur (hors de ce fichier) ne sont jamais touchées.
        """
        choice = (choice or "").strip()
        if not choice:
            return []
        proposed = {c.slug: c for c, _state in self.new_categories_report}
        if choice == "utiles":
            useful = {}
            for r in rows:
                if r["status_after"] != "actif" or r["action"] == DUP:
                    continue
                cats = list(r["categories_add"])
                if r.get("product") is not None:
                    cats += [link.category for link in r["product"].category_links.select_related("category__parent")]
                for c in cats:
                    if c.slug in proposed:
                        useful.setdefault(c.slug, proposed[c.slug])
            targets = list(useful.values())
        else:
            slugs = [s.strip() for s in choice.split(",") if s.strip()]
            unknown = [s for s in slugs if s not in self.by_slug]
            if unknown:
                raise CommandError(f"--rendre-visibles : catégorie(s) inconnue(s) : {', '.join(unknown)}")
            targets = [self.by_slug[s] for s in slugs]
        for c in list(targets):  # une sous-catégorie n'est visible que si sa parente l'est
            parent = c.parent if (c.parent_id or c._state.adding) else None
            if parent is not None and parent not in targets:
                targets.append(parent)
        out = [c for c in targets if not (c.pk and c.is_active)]
        shown = {c.slug for c in [*out, *targets]}
        for r in rows:  # ces produits seront dans le menu : la remarque « catégories masquées » ne s'applique plus
            cats = [*r["categories_add"]]
            if r.get("product") is not None:
                cats += [link.category for link in r["product"].category_links.all()]
            if any(c.slug in shown for c in cats):
                r["notes"] = [n for n in r["notes"] if "catégories masquées" not in n]
        return out

    def _apply_visibility(self):
        if not self.visible_plan:
            return
        slugs = [c.slug for c in self.visible_plan]
        Category.objects.filter(slug__in=slugs).update(is_active=True)
        log_action("category.show", target_type="catalog.category", changes={"slugs": slugs, "source": NOTE})

    def _render_categories(self, rows) -> list[str]:
        unmapped = Counter()
        undecided = Counter()
        refused = Counter()
        for r in rows:
            for name, cat, srcl in r["category_values"]:
                if srcl.startswith("liste produit"):
                    continue
                if cat is None and srcl.startswith("tableau"):
                    refused[name] += 1
                elif cat is None and _norm(name) in getattr(self, "mapping_rows", set()):
                    undecided[name] += 1
                elif cat is None or cat == "ambigu":
                    unmapped[name] += 1
        lines = [
            "",
            "## Catégories (correspondances explicites)",
            "",
            f"Tableau : {self.mapping_path or 'aucun'} · liste produit par produit :"
            f" {len(self.per_product)} appliqué(s), {self.per_product_skipped} non appliqué(s) (« appliquer = non »).",
            f"- Produits qui recevront au moins une catégorie : {sum(1 for r in rows if r['categories_add'])}",
            "",
            "Valeurs Shopify SANS correspondance (aucune catégorie Jodhur ; à décider dans le tableau) :",
        ]
        lines += [f"- {n} — {c} produit(s)" for n, c in (unmapped + undecided).most_common()] or ["- aucune"]
        lines += ["", "Valeurs marquées « aucune catégorie adaptée » dans le tableau :"]
        lines += [f"- {n} — {c} produit(s)" for n, c in refused.most_common()] or ["- aucune"]
        if self.new_categories_report:
            lines += [
                "",
                "Nouvelles catégories : " + ", ".join(f"{_cat_label(c)} ({s})" for c, s in self.new_categories_report),
            ]
        visible = {c.slug for c in self.visible_plan}
        counts = Counter()
        for r in rows:
            if r["status_after"] == "actif":
                cats = [*r["categories_add"]]
                if r.get("product") is not None:
                    cats += [link.category for link in r["product"].category_links.all()]
                for slug in {c.slug for c in cats} & visible:
                    counts[slug] += 1
        lines += ["", "### Catégories rendues visibles (avant l'activation des produits)", ""]
        verb = "rendue visible" if self.apply else "sera rendue visible"
        lines += [f"- {_cat_label(c)} (`{c.slug}`) : {verb} — {counts[c.slug]} produit(s) actif(s) directement"
                  for c in self.visible_plan] or ["- Aucune (option --rendre-visibles absente)."]  # fmt: skip
        hidden = sorted(
            _cat_label(c)
            for c, _s in self.new_categories_report
            if c.slug not in visible and not (c.pk and c.is_active)
        )
        if hidden:
            lines.append("- Restent masquées (aucun produit actif) : " + ", ".join(hidden))
        return lines

    def _render_images(self, rows) -> list[str]:
        dl = sum(len(r["images"]["download"]) for r in rows)
        link = sum(len(r["images"]["link"]) for r in rows)
        same = sum(len(r["images"]["same"]) for r in rows)
        alt = sum(r["images"]["alt_fallback"] for r in rows)
        failed = sum(r["images"].get("failed", 0) for r in rows)
        return [
            "",
            "## Images (stockées dans le projet, jamais servies depuis Shopify)",
            "",
            f"- À télécharger : {dl} · déjà présentes, reliées à leur image Shopify : {link} · déjà reliées : {same}"
            + (f" · échecs : {failed}" if self.apply else ""),
            f"- Sans texte alternatif dans Shopify (nom du produit utilisé) : {alt}",
        ]

    def _render_conflicts(self, rows) -> list[str]:
        kept = [(r, k) for r in rows for k in r["kept"]]
        lines = ["", "## Modifications Jodhur conservées (non écrasées)", ""]
        lines += [f"- {r['title']} : {k}" for r, k in kept] or ["- Aucune."]
        return lines

    def _render_misc(self, products, rows) -> list[str]:
        lines = ["", "## Autres points", ""]
        notes = Counter(n for r in rows for n in r["notes"] if not n.startswith(("identifiant URL Jodhur", "même nom")))
        lines += [f"- {n} ({c} produit(s))" for n, c in notes.most_common()] or ["- Aucun."]
        dups = [r for r in rows if r["action"] == DUP]
        if dups:
            lines += ["", "Doublons possibles (non importés, à traiter à la main) :"]
            lines += [f"- {r['title']} ↔ `{r['local']}` : {r.get('ambiguity', '?')}" for r in dups]
        if self.supplier_groups:
            lines += ["", "Vendors probablement identiques écrits différemment (marques différentes, non fusionnés) :"]
            lines += ["- " + " · ".join(f"« {g} »" for g in group) for group in self.supplier_groups]
        refs = Counter(m["type"] for p in products for m in p["metafields"] if "reference" in m["type"])
        if refs:
            lines += ["", "Metafields de type référence (stockés tels quels, non résolus) : "
                      + ", ".join(f"{t} ({n})" for t, n in refs.most_common())]  # fmt: skip
        return lines

    def _render_detail(self, rows) -> list[str]:
        lines = [
            "",
            "## Détail produit par produit",
            "",
            "| Produit | Fiche Jodhur | Résultat | Statut avant → après | Champs mis à jour | Gardé (Jodhur) |"
            " Catégories ajoutées | Images (télécharger / relier) | Points à vérifier |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for r in rows:
            cats = ", ".join(_cat_label(c) for c in r["categories_add"]) or "—"
            imgs = f"{len(r['images']['download'])} / {len(r['images']['link'])}"
            pts = "; ".join([*r["blocked"], *r["notes"]]) if r["status_after"] != "actif" else "; ".join(r["notes"])
            lines.append(
                f"| {_cell(r['title'], 60)} | `{r['local'] or r.get('slug', '—')}` | {r['result']}"
                f" | {r['status_before'] or '—'} → {r['status_after'] or '—'}"
                f" | {_cell('; '.join(r['changes']) or '—', 300)}"
                f" | {_cell('; '.join(r['kept']) or '—', 200)} | {_cell(cats)} | {imgs} | {_cell(pts or '—', 300)} |"
            )
        return lines

    def _csv(self, path: Path, rows):
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["produit", "handle", "fiche_jodhur", "resultat", "statut_avant", "statut_apres", "bloque_par",
                        "champs_mis_a_jour", "garde_jodhur", "categories_ajoutees", "images_a_telecharger",
                        "images_reliees", "variantes", "points_a_verifier"])  # fmt: skip
            for r in rows:
                w.writerow([r["title"], r["handle"], r["local"] or r.get("slug", ""), r["result"], r["status_before"],
                            r["status_after"], " ".join(r["blocked"]), "; ".join(r["changes"]), "; ".join(r["kept"]),
                            ", ".join(_cat_label(c) for c in r["categories_add"]), len(r["images"]["download"]),
                            len(r["images"]["link"]), len(r["p"]["variants"]) if "p" in r else "",
                            "; ".join(r["notes"])])  # fmt: skip
