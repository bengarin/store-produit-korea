"""
Importe les produits ACTIFS de Shopify dans le catalogue Jodhur, à partir d'un export en lecture seule
(backend/catalog_import/shopify/produits_actifs.json). Shopify n'est jamais modifié.

    python manage.py import_shopify --dry-run --report apercu_shopify.md   # aperçu : AUCUNE écriture
    python manage.py import_shopify --report rapport_shopify.md            # import réel (créations) + rapport
    python manage.py import_shopify --mettre-a-jour --report rapport.md    # + complète les produits existants

Règles :
- aucun doublon : un produit dont l'identifiant Shopify est déjà en base n'est jamais recréé ; un produit local
  sans identifiant Shopify, de même identifiant URL ou de même nom, n'est pas recréé non plus ;
- mise à jour des produits existants (seulement avec --mettre-a-jour, toujours visible dans l'aperçu) :
  · produit relié par son identifiant Shopify, ou relié s'il correspond à UN SEUL produit local (même identifiant
    URL ou même nom) sans ambiguïté — l'identifiant Shopify est alors enregistré sur la fiche ;
  · seuls le fournisseur (s'il est vide), les collections (ajout uniquement) et la catégorie (seulement si le
    produit n'en a AUCUNE et qu'une correspondance est claire) sont complétés ; un fournisseur ou une catégorie
    choisis dans l'admin ne sont jamais remplacés ; un fournisseur, une collection ou une catégorie retirés à la
    main après un import précédent ne sont pas remis (historique d'audit) ; nom, textes, prix, stock, variantes,
    images, statut et marque ne sont jamais touchés ;
- produit créé en BROUILLON (rien n'apparaît sur la boutique sans relecture) ; fournisseur = « Vendor » Shopify ;
  marque laissée vide (Shopify n'en fournit pas) ; aucune donnée inventée ;
- variantes, prix, prix barrés et stock Shopify conservés ; chaque stock importé est tracé (« Premier comptage ») ;
  SKU repris s'il existe et n'est pas déjà utilisé ;
- images téléchargées depuis cdn.shopify.com (HTTPS uniquement), ré-encodées en WebP ; une image en échec est
  signalée, le produit est quand même créé ;
- fournisseur = « Vendor » Shopify ; la MARQUE est un autre champ, jamais déduit du fournisseur ;
- collections : une collection Shopify est reliée à une collection Jodhur seulement si leurs noms sont identiques
  (majuscules, accents et ponctuation ignorés) ; aucune collection n'est créée ; les autres sont listées
  « à traiter » ; les règles d'entrée de la collection Jodhur (pays, ingrédients) sont respectées ;
- catégories : seulement si UNE catégorie Jodhur porte le même nom (majuscules, accents et ponctuation ignorés)
  qu'une collection Shopify ou que le dernier niveau de la catégorie Shopify ; sinon aucune (à choisir dans
  l'admin). Rien n'est déduit d'un nom proche.
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

from apps.audit.models import AuditLog
from apps.audit.services import log_action
from apps.catalog.models import (
    Category,
    Collection,
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
ACTION_CREATE = "product.import_shopify"
ACTION_UPDATE = "product.import_shopify_update"
CREATE = "créer"
UPDATE = "mettre à jour"
LINK = "relier + mettre à jour"
UP_TO_DATE = "déjà à jour"


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
        parser.add_argument(
            "--mettre-a-jour",
            action="store_true",
            help="Complète aussi les produits déjà présents (fournisseur vide, collections) sans rien écraser.",
        )

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
        self.update = opts["mettre_a_jour"]
        cats = {}
        for c in Category.objects.select_related("parent"):
            cats.setdefault(_norm(c.name), []).append(c)
        self.categories = cats  # nom normalisé → catégories Jodhur (plusieurs = ambigu, jamais choisie)
        by_name = {}
        for c in Collection.objects.all():
            by_name.setdefault(_norm(c.name), []).append(c)
        self.collections = by_name  # nom normalisé → collections Jodhur (plusieurs = ambigu, jamais relié)

        rows = [self._analyse(p) for p in products]
        self._flag_source_duplicates(products, rows)
        if not self.dry:
            for p, row in zip(products, rows, strict=True):
                if row["action"] == CREATE:
                    self._create(p, row)
                elif row["action"] in (UPDATE, LINK) and self.update:
                    self._apply_update(p, row)
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
            "action": CREATE,
            "collection_matches": self._match_collections(p),
            "category_matches": self._match_categories(p),
        }
        existing = Product.objects.filter(shopify_id=p["id"]).first()
        if existing:
            row["action"] = UPDATE
            row["local"] = existing.slug
            row["plan"] = self._plan_update(existing, row)
            if not row["plan"]["changes"]:
                row["action"] = UP_TO_DATE
            return row
        title = p["title"].strip()
        candidates = list(
            Product.objects.filter(slug=p["handle"])
            | Product.objects.filter(name__iexact=title)
            | Product.objects.filter(display_name__iexact=title)
        )
        if candidates:
            row["local"] = ", ".join(c.slug for c in candidates)
            if len(candidates) == 1 and not candidates[0].shopify_id:
                row["action"] = LINK
                row["link_pk"] = candidates[0].pk
                row["plan"] = self._plan_update(candidates[0], row, link=p["id"])
                local = candidates[0].public_name.strip()
                warnings.append(f"produit local « {local} » ({candidates[0].slug}) : même identifiant URL ou même nom")
            else:
                row["action"] = "doublon possible (non importé)"
                why = "déjà relié à un autre produit Shopify" if len(candidates) == 1 else "plusieurs produits locaux"
                row["ambiguity"] = why
                warnings.append(f"correspondance ambiguë ({why}) : {row['local']} — à traiter à la main")
            return row
        if not row["vendor"]:
            warnings.append("fournisseur manquant")
        if not row["images"]:
            warnings.append("aucune image")
        if not _plain(p.get("descriptionHtml")):
            warnings.append("description manquante")
        cats = self._matching_categories(p)
        row["jodhur_categories"] = [c.name for c in cats]
        if not cats:
            warnings.append("catégorie Jodhur à choisir (aucune correspondance claire)")
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

    def _match_collections(self, p: dict) -> list[tuple[str, object]]:
        """(collection Shopify, collection Jodhur | None | "ambigu") — noms identiques seulement, rien n'est deviné."""
        out = []
        for name in p.get("collections") or []:
            found = self.collections.get(_norm(name)) or []
            out.append((name, found[0] if len(found) == 1 else ("ambigu" if found else None)))
        return out

    def _history(self, product: Product) -> dict:
        """Ce que les imports précédents ont déjà posé sur ce produit (pour ne pas remettre un retrait manuel)."""
        logs = AuditLog.objects.filter(
            target_type="catalog.product", target_id=str(product.pk), action__in=[ACTION_CREATE, ACTION_UPDATE]
        )
        supplier, collections, categories = False, set(), set()
        for log in logs:
            supplier = supplier or bool((log.changes or {}).get("supplier"))
            collections.update((log.changes or {}).get("collectionsAdded") or [])
            categories.update((log.changes or {}).get("categoriesAdded") or [])
        return {"supplier": supplier, "collections": collections, "categories": categories}

    def _plan_update(self, product: Product, row: dict, link: str | None = None) -> dict:
        """Ce qui serait complété sur un produit existant. Ne lit que la base : aucune écriture."""
        history = self._history(product)
        vendor = row["vendor"][:150]
        plan = {
            "pk": product.pk,
            "link": link,
            "supplier": None,
            "add": [],
            "categories": [],
            "kept": [],
            "changes": [],
        }
        plan["current_categories"] = [
            _cat_label(pc.category)
            for pc in ProductCategory.objects.filter(product=product)
            .select_related("category__parent")
            .order_by("position", "id")
        ]
        local = product.supplier.strip()
        if vendor and not local:
            if history["supplier"]:
                plan["kept"].append("fournisseur effacé à la main après un import : laissé vide")
            else:
                plan["supplier"] = vendor
                plan["changes"].append(f"fournisseur → « {vendor} »")
        elif vendor and local != vendor:
            plan["kept"].append(f"fournisseur local « {local} » conservé (Shopify : « {vendor} »)")
        current = set(product.collections.values_list("pk", flat=True))
        for _name, coll in row["collection_matches"]:
            if not isinstance(coll, Collection) or coll.pk in current or coll in plan["add"]:
                continue
            if coll.pk in history["collections"]:
                plan["kept"].append(f"« {coll.name} » retirée à la main après un import : non remise")
                continue
            errors = coll.entry_errors(origin=product.origin_country, ingredients=product.ingredients)
            if errors:
                plan["kept"].append("collection non ajoutée — " + " ".join(errors))
                continue
            plan["add"].append(coll)
            plan["changes"].append(f"collection + « {coll.name} »")
        clear = self._matching_categories_from(row["category_matches"])
        if plan["current_categories"]:
            if clear and {_cat_label(c) for c in clear} - set(plan["current_categories"]):
                plan["kept"].append(
                    "catégorie(s) déjà choisie(s) dans Jodhur conservée(s) (proposition ignorée : "
                    + ", ".join(_cat_label(c) for c in clear)
                    + ")"
                )
        else:
            removed = [c for c in clear if c.pk in history["categories"]]
            if removed:
                plan["kept"].append("catégorie(s) retirée(s) à la main après un import : non remise(s)")
            else:
                plan["categories"] = clear
                plan["changes"] += [f"catégorie + « {_cat_label(c)} »" for c in clear]
        if link:
            plan["changes"].insert(0, "identifiant Shopify enregistré")
        return plan

    def _match_categories(self, p: dict) -> list[tuple[str, object]]:
        """
        (nom Shopify, catégorie Jodhur | None | "ambigu"). Sources : les collections Shopify et le dernier niveau de
        la catégorie Shopify. Une correspondance est « claire » seulement si UNE catégorie Jodhur porte le même nom
        (majuscules, accents et ponctuation ignorés) ; rien n'est déduit d'un nom proche.
        """
        names = [*(p.get("collections") or [])]
        if p.get("category"):
            names.append(p["category"].split(">")[-1].strip())
        out = []
        for name in names:
            found = self.categories.get(_norm(name)) or []
            out.append((name, found[0] if len(found) == 1 else ("ambigu" if found else None)))
        return out

    @staticmethod
    def _matching_categories_from(matches) -> list:
        found = []
        for _name, cat in matches:
            if isinstance(cat, Category) and cat not in found:
                found.append(cat)
        return found

    def _matching_categories(self, p: dict) -> list:
        return self._matching_categories_from(self._match_categories(p))

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
        # Une liaison n'est faite que si elle est sans ambiguïté des deux côtés.
        claims = Counter(r["link_pk"] for r in rows if r["action"] == LINK)
        for p, row in zip(products, rows, strict=True):
            if row["action"] != LINK:
                continue
            reason = ""
            if titles[p["title"].strip().lower()] > 1:
                reason = "plusieurs produits Shopify portent ce nom"
            elif claims[row["link_pk"]] > 1:
                reason = "le même produit local correspond à plusieurs produits Shopify"
            if reason:
                row["action"] = "doublon possible (non importé)"
                row["ambiguity"] = reason
                row.pop("plan", None)
                row["warnings"].append(f"correspondance ambiguë ({reason}) : {row['local']} — à traiter à la main")

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
        new_cats = self._matching_categories(p)
        for i, cat in enumerate(new_cats):
            ProductCategory.objects.create(product=product, category=cat, position=i)
        added = []
        for _name, coll in row["collection_matches"]:
            if not isinstance(coll, Collection) or coll in added:
                continue
            errors = coll.entry_errors(origin=product.origin_country, ingredients=product.ingredients)
            if errors:
                row["warnings"].append("collection non ajoutée — " + " ".join(errors))
            else:
                added.append(coll)
        product.collections.add(*added)
        row["collections_added"] = [c.name for c in added]

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
            ACTION_CREATE,
            target=product,
            changes={
                "shopifyId": p["id"],
                "supplier": product.supplier,
                "variants": len(p["variants"]),
                "collectionsAdded": [c.pk for c in added],
                "categoriesAdded": [c.pk for c in new_cats],
            },
        )
        return product

    # --- Mise à jour d'un produit existant (fournisseur vide, collections, catégorie si aucune) --------
    def _apply_update(self, p: dict, row: dict):
        try:
            with transaction.atomic():
                product = Product.objects.select_for_update().get(pk=row["plan"]["pk"])
                plan = self._plan_update(product, row, link=row["plan"]["link"])  # recalculé sous verrou
                fields = []
                if plan["link"]:
                    if product.shopify_id or Product.objects.filter(shopify_id=plan["link"]).exists():
                        raise ValueError("identifiant Shopify déjà utilisé : liaison annulée")
                    product.shopify_id = plan["link"]
                    fields.append("shopify_id")
                if plan["supplier"]:
                    product.supplier = plan["supplier"]
                    fields.append("supplier")
                if fields:
                    product.save(update_fields=[*fields, "updated_at"])
                product.collections.add(*plan["add"])
                if plan["categories"]:
                    if ProductCategory.objects.filter(product=product).exists():
                        raise ValueError("catégorie ajoutée entre-temps dans Jodhur : rien n'est remplacé")
                    for i, cat in enumerate(plan["categories"]):
                        ProductCategory.objects.create(product=product, category=cat, position=i)
                if plan["changes"]:
                    log_action(
                        ACTION_UPDATE,
                        target=product,
                        changes={
                            "shopifyId": p["id"],
                            "linked": bool(plan["link"]),
                            "supplier": plan["supplier"] or "",
                            "collectionsAdded": [c.pk for c in plan["add"]],
                            "categoriesAdded": [c.pk for c in plan["categories"]],
                        },
                    )
        except Exception as exc:  # noqa: BLE001 — un produit en échec n'arrête pas l'import
            row["action"] = "échec"
            row["warnings"].append(f"erreur : {exc}")
            return
        row["plan"] = plan
        row["action"] = "mis à jour" if plan["changes"] else UP_TO_DATE

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
            "Règles : produits créés en brouillon ; fournisseur = « Vendor » Shopify (la marque est un autre champ,"
            " laissée vide) ; collections reliées seulement si le nom est identique ; aucune collection créée ;"
            " produits existants : seuls le fournisseur vide, les collections et la catégorie (si aucune)"
            " sont complétés (avec --mettre-a-jour) ;"
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
        lines += [
            f"- **{r['title']}** ↔ produit local `{r['local']}` (non importé, non relié : correspondance ambiguë —"
            f" {r.get('ambiguity', '?')} ; à traiter à la main)"
            for r in dup_local
        ] or ["- Aucun doublon avec le catalogue Jodhur actuel."]
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
        lines += self._render_suppliers(rows)
        lines += self._render_categories(products, rows)
        lines += self._render_collections(products, rows)
        lines += self._render_updates(rows)
        lines += self._render_detail(rows)
        lines += [
            "",
            "## Produits",
            "",
            "| Produit | Fournisseur | Variantes (titre · SKU · prix DH · stock) | Images | Catégorie Shopify"
            " | Catégorie Jodhur | Collections Jodhur | Action | Points à vérifier |",
            "|---|---|---|---|---|---|---|---|---|",
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
                f" | {_cell(', '.join(r.get('jodhur_categories') or []) or '—')}"
                f" | {_cell(', '.join(self._collections_for(r)) or '—')} | {r['action']}"
                f" | {_cell(notes or '—')} |"
            )
        return "\n".join(lines) + "\n"

    def _collections_for(self, r: dict) -> list[str]:
        """Collections Jodhur posées (import réel) ou prévues (aperçu) pour cette ligne."""
        if "plan" in r:
            return [c.name for c in r["plan"]["add"]]
        if "collections_added" in r:
            return r["collections_added"]
        if r["action"] != CREATE:
            return []
        return [
            c.name
            for _n, c in r["collection_matches"]
            if isinstance(c, Collection) and not c.entry_errors(origin="", ingredients=[])
        ]

    def _render_suppliers(self, rows) -> list[str]:
        new = [r for r in rows if r["action"] in (CREATE, "créé (brouillon)")]
        planned = [r for r in rows if r.get("plan")]
        fill = [r for r in planned if r["plan"]["supplier"]]
        kept = [(r, k) for r in planned for k in r["plan"]["kept"] if k.startswith("fournisseur")]
        same = len(planned) - len(fill) - len({id(r) for r, _k in kept})
        lines = [
            "",
            "## Fournisseur (« Vendor » Shopify → champ Fournisseur Jodhur)",
            "",
            "La marque n'est jamais remplie à partir du fournisseur : ce sont deux champs différents.",
            "",
            f"- Nouveaux produits avec fournisseur : {sum(1 for r in new if r['vendor'])} / {len(new)}",
            f"- Produits existants dont le fournisseur vide sera complété : {len(fill)}",
            f"- Produits existants au fournisseur déjà identique (ou absent dans Shopify) : {same}",
            f"- Fournisseur local différent ou effacé à la main (conservé, non remplacé) : {len(kept)}",
        ]
        lines += [f"  - {r['title']} : {k}" for r, k in kept]
        lines += ["", "| Fournisseur Shopify | Produits |", "|---|---|"]
        lines += [f"| {_cell(v or '(vide)')} | {n} |" for v, n in Counter(r["vendor"] for r in rows).most_common()]
        return lines

    def _render_collections(self, products, rows) -> list[str]:
        counts = Counter(c for p in products for c in (p.get("collections") or []))
        status = {}
        for r in rows:
            for name, coll in r["collection_matches"]:
                status[name] = coll
        linked = [n for n in counts if isinstance(status.get(n), Collection)]
        todo = [n for n in counts if n not in linked]
        existing = ", ".join(f"« {c.name} »" for cs in self.collections.values() for c in cs) or "aucune"
        lines = [
            "",
            "## Collections Shopify → Collections Jodhur",
            "",
            f"Collections Jodhur existantes : {existing}. Aucune collection n'est créée par l'import.",
            f"Reliées (nom identique) : {len(linked)} · à traiter : {len(todo)} sur {len(counts)} collections Shopify.",
            "",
            "| Collection Shopify | Produits | Collection Jodhur | Statut |",
            "|---|---|---|---|",
        ]
        for name, n in counts.most_common():
            coll = status.get(name)
            if isinstance(coll, Collection):
                lines.append(f"| {_cell(name)} | {n} | {_cell(coll.name)} | reliée |")
            elif coll == "ambigu":
                lines.append(f"| {_cell(name)} | {n} | — | à traiter : plusieurs collections Jodhur de ce nom |")
            else:
                lines.append(f"| {_cell(name)} | {n} | — | à traiter : aucune collection Jodhur de ce nom |")
        blocked = Counter(k for r in rows for k in r.get("plan", {}).get("kept", []) if k.startswith("collection"))
        blocked.update(w for r in rows for w in r["warnings"] if w.startswith("collection non ajoutée"))
        if blocked:
            lines += ["", "Ajouts refusés par les règles de la collection Jodhur :"]
            lines += [f"- {k} ({n} produit(s))" for k, n in blocked.most_common()]
        return lines

    def _render_updates(self, rows) -> list[str]:
        planned = [r for r in rows if r.get("plan")]
        if self.dry:
            note = "Aperçu : rien n'est écrit. Appliqué seulement avec l'option --mettre-a-jour."
        elif self.update:
            note = "Appliqué."
        else:
            note = "NON appliqué (option --mettre-a-jour absente)."
        lines = [
            "",
            "## Produits déjà présents dans Jodhur (mise à jour)",
            "",
            note + " Seuls l'identifiant Shopify, le fournisseur vide, les collections et la catégorie (si le produit"
            " n'en a aucune) sont complétés ; nom, textes, prix, stock, variantes, images, statut et marque ne sont"
            " jamais touchés.",
            "",
            f"- Reliés par identifiant Shopify : {sum(1 for r in planned if not r['plan']['link'])}"
            f" · à relier (même identifiant URL ou même nom, sans ambiguïté) :"
            f" {sum(1 for r in planned if r['plan']['link'])}"
            f" · avec des changements : {sum(1 for r in planned if r['plan']['changes'])}",
        ]
        fields = Counter(c.split(" ")[0] for r in planned for c in r["plan"]["changes"])
        lines.append(
            "- Champs qui seront modifiés : "
            + (", ".join(f"{k} ({n})" for k, n in fields.most_common()) or "aucun")
            + " — détail produit par produit ci-dessous."
        )
        return lines

    def _render_categories(self, products, rows) -> list[str]:
        sources = Counter()
        status = {}
        for r in rows:
            for name, cat in r["category_matches"]:
                sources[name] += 1
                status[name] = cat
        clear = [(n, status[n]) for n in sources if isinstance(status[n], Category)]
        ambiguous = [n for n in sources if status[n] == "ambigu"]
        existing = ", ".join(_cat_label(c) for cs in self.categories.values() for c in cs) or "aucune"
        planned = [r for r in rows if r.get("plan")]
        lines = [
            "",
            "## Catégories Jodhur (proposées à partir des collections et de la catégorie Shopify)",
            "",
            f"Catégories Jodhur existantes : {existing}.",
            "Une catégorie est proposée seulement si une catégorie Jodhur porte EXACTEMENT le même nom (majuscules,"
            " accents et ponctuation ignorés) qu'une collection Shopify ou que le dernier niveau de la catégorie"
            " Shopify. Aucune catégorie n'est créée ni déduite d'un nom proche. Un produit qui a déjà une catégorie"
            " dans Jodhur la garde (aucun ajout, aucun remplacement).",
            "",
            f"- Correspondances claires : {len(clear)} nom(s) Shopify"
            + ("".join(f"\n  - « {n} » → {_cat_label(c)} ({sources[n]} produit(s))" for n, c in clear) or ""),
            f"- Noms ambigus (plusieurs catégories Jodhur de ce nom, rien proposé) : {', '.join(ambiguous) or 'aucun'}",
            f"- Produits existants qui recevront une catégorie : {sum(1 for r in planned if r['plan']['categories'])}",
            f"- Produits existants sans catégorie et sans correspondance claire (à choisir à la main) : "
            f"{sum(1 for r in planned if not r['plan']['categories'] and not r['plan']['current_categories'])}",
            f"- Produits existants qui gardent leur catégorie Jodhur : "
            f"{sum(1 for r in planned if r['plan']['current_categories'])}",
        ]
        return lines

    def _render_detail(self, rows) -> list[str]:
        lines = [
            "",
            "## Prévisualisation détaillée par produit",
            "",
            "| Produit | Fiche Jodhur | Collections Shopify | Catégorie Shopify | Catégorie(s) Jodhur actuelle(s)"
            " | Catégorie Jodhur proposée | Champs modifiés | Conservé tel quel / à traiter |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in rows:
            plan = r.get("plan")
            if plan:
                current = ", ".join(plan["current_categories"]) or "aucune"
                proposed = ", ".join(_cat_label(c) for c in plan["categories"]) or (
                    "— (garde l'actuelle)" if plan["current_categories"] else "aucune correspondance claire"
                )
                changes = "; ".join(plan["changes"]) or "aucun"
                kept = "; ".join(plan["kept"]) or "—"
            else:
                current = "— (nouveau)" if r["action"] in (CREATE, "créé (brouillon)") else "—"
                cats = r.get("jodhur_categories") or []
                proposed = ", ".join(cats) or "aucune correspondance claire"
                changes = "création (brouillon)" if r["action"] in (CREATE, "créé (brouillon)") else r["action"]
                kept = "; ".join(w for w in r["warnings"] if not w.startswith(("marque", "SKU manquant"))) or "—"
            lines.append(
                f"| {_cell(r['title'], 60)} | `{r.get('local', '—')}`"
                f" | {_cell(', '.join(r['collections']) or '—', 300)}"
                f" | {_cell(r['category'].split('>')[-1].strip() or '—', 60)} | {_cell(current, 120)}"
                f" | {_cell(proposed, 120)} | {_cell(changes, 300)} | {_cell(kept, 300)} |"
            )
        lines += ["", "La marque n'est jamais modifiée par l'import (Shopify n'a pas de champ marque)."]
        return lines

    def _csv(self, path: Path, rows):
        import csv

        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(
                ["produit", "handle", "fournisseur", "variante", "sku", "prix", "prix_barre", "stock", "images",
                 "categorie_shopify", "collections_shopify", "categorie_jodhur_actuelle", "categorie_jodhur_proposee",
                 "collections_jodhur", "action", "changements", "a_verifier"]
            )  # fmt: skip
            for r in rows:
                plan = r.get("plan") or {}
                if plan:
                    cats = [", ".join(plan["current_categories"]), ", ".join(_cat_label(c) for c in plan["categories"])]
                else:
                    cats = ["", ", ".join(r.get("jodhur_categories") or [])]
                common = [*cats, ", ".join(self._collections_for(r)), r["action"], "; ".join(plan.get("changes", []))]
                if not r["variants"]:
                    w.writerow(
                        [r["title"], r["handle"], r["vendor"], "", "", "", "", "", r["images"], r["category"],
                         " | ".join(r["collections"]), *common, "; ".join(r["warnings"] + plan.get("kept", []))]
                    )  # fmt: skip
                for v in r["variants"]:
                    w.writerow(
                        [r["title"], r["handle"], r["vendor"], v["title"], v["sku"], v["price"], v["compare"] or "",
                         v["stock"], r["images"], r["category"], " | ".join(r["collections"]), *common,
                         "; ".join(r["warnings"] + [v.get("sku_note", ""), v.get("stock_note", "")]).strip("; ")]
                    )  # fmt: skip


def _cat_label(cat) -> str:
    return f"{cat.parent.name} › {cat.name}" if cat.parent_id else cat.name


def _cell(value, size=80) -> str:
    text = str(value).replace("|", "/").replace("\n", " ")
    return text if len(text) <= size else text[: size - 1] + "…"
