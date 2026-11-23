"""
Lecture des produits Shopify ACTIFS, en lecture seule :
- soit directement par l'API Admin GraphQL (pagination, nouvelles tentatives) ;
- soit depuis un export JSON (même format : liste des nœuds produits renvoyés par la requête ci-dessous).

Puis normalisation en un dictionnaire simple utilisé par la commande `import_shopify`.
Shopify n'est JAMAIS modifié : la seule requête envoyée est une requête de lecture (`query`).
"""

import json
import re
import time
import urllib.error
import urllib.request
from html import unescape

PRODUCTS_QUERY = """
query Produits($first: Int!, $after: String) {
  products(first: $first, after: $after, query: "status:active", sortKey: ID) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id handle title status vendor productType tags descriptionHtml updatedAt
      category { id fullName }
      seo { title description }
      options { name position values }
      collections(first: 100) { pageInfo { hasNextPage } nodes { id title handle } }
      media(first: 100) {
        pageInfo { hasNextPage }
        nodes { id mediaContentType alt ... on MediaImage { image { url width height altText } } }
      }
      metafields(first: 100) { pageInfo { hasNextPage } nodes { id namespace key type value } }
      variants(first: 100) {
        pageInfo { hasNextPage }
        nodes {
          id title sku position price compareAtPrice inventoryQuantity inventoryPolicy
          barcodes(first: 5) { nodes { type value } }
          selectedOptions { name value }
          media(first: 1) { nodes { id } }
          inventoryItem { tracked measurement { weight { unit value } } }
        }
      }
    }
  }
}
"""

DEFAULT_TITLE = "Default Title"
WEIGHT_TO_GRAMS = {"GRAMS": 1, "KILOGRAMS": 1000, "OUNCES": 28.3495, "POUNDS": 453.592}


class SourceError(Exception):
    pass


def fetch_from_api(domain: str, token: str, version: str, page_size: int = 10, log=print) -> list[dict]:
    """Tous les produits actifs, page par page. 429 / 5xx / THROTTLED → nouvelles tentatives (5 max)."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.myshopify\.com", domain or ""):
        raise SourceError("SHOPIFY_STORE_DOMAIN doit être du type « ma-boutique.myshopify.com ».")
    if not token:
        raise SourceError("SHOPIFY_ADMIN_TOKEN manquant (jeton d'une application personnalisée, droit read_products).")
    url = f"https://{domain}/admin/api/{version}/graphql.json"
    nodes, after, page = [], None, 0
    while True:
        page += 1
        body = json.dumps({"query": PRODUCTS_QUERY, "variables": {"first": page_size, "after": after}}).encode()
        data = _post_with_retries(url, token, body)
        products = data["data"]["products"]
        nodes += products["nodes"]
        log(f"  page {page} : {len(products['nodes'])} produit(s) (total {len(nodes)})")
        if not products["pageInfo"]["hasNextPage"]:
            return nodes
        after = products["pageInfo"]["endCursor"]


def _post_with_retries(url: str, token: str, body: bytes, attempts: int = 5) -> dict:
    delay = 2.0
    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(  # noqa: S310 (hôte *.myshopify.com vérifié)
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "X-Shopify-Access-Token": token},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (hôte *.myshopify.com vérifié)
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < attempts:
                time.sleep(delay)
                delay *= 2
                continue
            raise SourceError(f"Shopify a répondu {exc.code} : {exc.reason}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < attempts:
                time.sleep(delay)
                delay *= 2
                continue
            raise SourceError(f"Connexion à Shopify impossible : {exc}") from exc
        errors = data.get("errors") or []
        if any((e.get("extensions") or {}).get("code") == "THROTTLED" for e in errors) and attempt < attempts:
            time.sleep(delay)
            delay *= 2
            continue
        if errors:
            raise SourceError("Erreur GraphQL Shopify : " + "; ".join(e.get("message", "?") for e in errors))
        return data
    raise SourceError("Shopify : trop de tentatives.")


def load_file(path) -> tuple[dict, list[dict]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    nodes = doc.get("products") or []
    if nodes and "media" not in nodes[0]:
        raise SourceError(
            "Ancien format d'export (sans images ni metafields complets) : utilisez l'export complet"
            " (catalog_import/shopify/export_shopify_complet.json) ou --source shopify."
        )
    return doc, nodes


# --- Normalisation ----------------------------------------------------------------------------------
def normalize(node: dict) -> dict:
    """Nœud GraphQL → dictionnaire simple. Signale les listes tronquées (plus de 100 éléments)."""
    truncated = [k for k in ("collections", "media", "metafields", "variants") if node[k]["pageInfo"]["hasNextPage"]]
    images = []
    for position, m in enumerate(node["media"]["nodes"]):
        if m.get("mediaContentType") != "IMAGE" or not (m.get("image") or {}).get("url"):
            continue
        images.append({
            "id": m["id"],
            "url": m["image"]["url"],
            "alt": (m.get("alt") or m["image"].get("altText") or "").strip(),
            "position": position,
        })  # fmt: skip
    variants = []
    for v in sorted(node["variants"]["nodes"], key=lambda v: v.get("position") or 0):
        weight = ((v.get("inventoryItem") or {}).get("measurement") or {}).get("weight") or {}
        grams = None
        if weight.get("value"):
            grams = round(float(weight["value"]) * WEIGHT_TO_GRAMS.get(weight.get("unit"), 0)) or None
        barcodes = [b["value"].strip() for b in (v.get("barcodes") or {}).get("nodes", []) if b.get("value")]
        if not barcodes and v.get("barcode"):  # anciennes versions de l'API : champ simple
            barcodes = [v["barcode"].strip()]
        variants.append({
            "id": v["id"],
            "title": "" if v["title"] == DEFAULT_TITLE else v["title"],
            "sku": (v.get("sku") or "").strip(),
            "barcode": barcodes[0] if barcodes else "",
            "price": v["price"],
            "compareAtPrice": v.get("compareAtPrice"),
            "inventoryQuantity": v.get("inventoryQuantity"),
            "tracked": bool((v.get("inventoryItem") or {}).get("tracked")),
            "backorder": v.get("inventoryPolicy") == "CONTINUE",
            "options": [o for o in v.get("selectedOptions") or [] if o["value"] != DEFAULT_TITLE],
            "mediaId": ((v.get("media") or {}).get("nodes") or [{}])[0].get("id"),
            "weightGrams": grams,
        })  # fmt: skip
    options = [o for o in node.get("options") or [] if not (o["name"] == "Title" and o["values"] == [DEFAULT_TITLE])]
    seo = node.get("seo") or {}
    return {
        "id": node["id"],
        "handle": node["handle"],
        "title": node["title"].strip(),
        "status": node["status"],
        "vendor": (node.get("vendor") or "").strip(),
        "productType": (node.get("productType") or "").strip(),
        "category": ((node.get("category") or {}).get("fullName") or "").strip(),
        "tags": list(node.get("tags") or []),
        "descriptionHtml": node.get("descriptionHtml") or "",
        "updatedAt": node.get("updatedAt"),
        "seoTitle": (seo.get("title") or "").strip(),
        "seoDescription": (seo.get("description") or "").strip(),
        "collections": [c["title"] for c in node["collections"]["nodes"]],
        "options": options,
        "images": images,
        "variants": variants,
        "metafields": [
            {"id": m["id"], "namespace": m["namespace"], "key": m["key"], "type": m["type"], "value": m["value"] or ""}
            for m in node["metafields"]["nodes"]
        ],
        "truncated": truncated,
    }


# --- Conversions de texte (aucun contenu n'est rédigé : on ne fait que changer de format) -------------
def plain_text(html: str) -> str:
    text = re.sub(r"<(br|/p|/li|/h[1-6]|/div)[^>]*>", "\n", html or "", flags=re.I)
    text = unescape(re.sub(r"<[^>]+>", "", text))
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def first_paragraph(html: str) -> str:
    lines = plain_text(html).split("\n")
    return lines[0][:1000] if lines and lines[0] else ""


def rich_text_lines(value: str) -> list[str]:
    """Metafield « rich_text » / « multi_line » de Shopify (JSON) → lignes de texte simple."""
    if not value:
        return []
    try:
        root = json.loads(value)
    except (TypeError, ValueError):
        return [line.strip() for line in str(value).splitlines() if line.strip()]
    blocks = []

    def walk(node, buf):
        if node.get("type") == "text":
            buf.append(node.get("value") or "")
            return
        if node.get("type") in ("paragraph", "list-item", "heading"):
            inner = []
            for child in node.get("children") or []:
                walk(child, inner)
            blocks.append("".join(inner))
            return
        for child in node.get("children") or []:
            walk(child, buf)

    walk(root, [])
    lines = []
    for block in blocks:
        lines += [line.strip() for line in block.split("\n") if line.strip()]
    return lines


def bullet_free(lines: list[str]) -> list[str]:
    return [re.sub(r"^[✓✔✦•\-–*]\s*", "", line).strip() for line in lines if line.strip()]


def cut(text: str, size: int) -> tuple[str, bool]:
    """Coupe au dernier mot entier sous la limite. Retourne (texte, coupé ?)."""
    text = (text or "").strip()
    if len(text) <= size:
        return text, False
    short = text[: size - 1].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"
    return short, True
