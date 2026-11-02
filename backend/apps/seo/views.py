"""
Référencement : la boutique est une application React (une seule page HTML). Pour que Google, Bing, Facebook,
WhatsApp… reçoivent les VRAIES informations de chaque page SANS exécuter JavaScript, Django renvoie le index.html
construit par Vite (FRONTEND_DIST_DIR) en y injectant, selon l'URL :
- <title>, meta description, URL canonique, Open Graph / Twitter ;
- données structurées schema.org Product (prix, devise MAD, disponibilité) sur les fiches produit ;
- un résumé <noscript> (nom, description, prix) pour les robots qui n'exécutent pas JavaScript ;
- robots noindex sur les pages privées (panier, commande, administration) ;
- 404 (produit inconnu ou brouillon) et 410 (produit archivé), avec noindex.
Plus /sitemap.xml et /robots.txt.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from django.conf import settings
from django.http import Http404, HttpResponse
from django.utils.html import escape

from apps.catalog import public
from apps.catalog.models import Category, Product

PRIVATE_PREFIXES = ("/panier", "/commande", "/confirmation", "/admin")
DEFAULT_DESCRIPTION = (
    "Ma Petite Corée — soins coréens et naturels. Livraison partout au Maroc, paiement à la livraison."
)


@lru_cache(maxsize=4)
def _template(path: str, mtime: float) -> str:
    return Path(path).read_text(encoding="utf-8")


def index_html() -> str:
    path = Path(settings.FRONTEND_DIST_DIR) / "index.html"
    if not path.exists():
        raise Http404("index.html introuvable (lancer `npm run build` et régler FRONTEND_DIST_DIR).")
    return _template(str(path), path.stat().st_mtime)


def site_url(request) -> str:
    return (settings.SITE_URL or request.build_absolute_uri("/")).rstrip("/")


def absolute(base: str, url: str | None) -> str | None:
    if not url:
        return None
    return url if url.startswith(("http://", "https://")) else f"{base}{url}"


def json_ld(data: dict) -> str:
    # Pas de « </script> » possible dans le JSON : < > & échappés en unicode.
    text = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f'<script type="application/ld+json">{text}</script>'


def render(
    request,
    *,
    title,
    description,
    canonical=None,
    image=None,
    og_type="website",
    noindex=False,
    extra_head="",
    noscript="",
    status=200,
) -> HttpResponse:
    html = index_html()
    # Retire le titre et la description par défaut de index.html : remplacés par ceux de la page.
    html = re.sub(r"<title>.*?</title>", "", html, count=1, flags=re.S)
    html = re.sub(r'<meta name="description"[^>]*>', "", html, count=1)
    tags = [f"<title>{escape(title)}</title>", f'<meta name="description" content="{escape(description)}" />']
    if noindex:
        tags.append('<meta name="robots" content="noindex, nofollow" />')
    if canonical:
        tags.append(f'<link rel="canonical" href="{escape(canonical)}" />')
    tags += [
        f'<meta property="og:site_name" content="{escape(settings.SITE_NAME)}" />',
        f'<meta property="og:title" content="{escape(title)}" />',
        f'<meta property="og:description" content="{escape(description)}" />',
        f'<meta property="og:type" content="{og_type}" />',
        '<meta property="og:locale" content="fr_MA" />',
        f'<meta name="twitter:card" content="{"summary_large_image" if image else "summary"}" />',
    ]
    if canonical:
        tags.append(f'<meta property="og:url" content="{escape(canonical)}" />')
    if image:
        tags.append(f'<meta property="og:image" content="{escape(image)}" />')
    html = html.replace("</head>", "    " + "\n    ".join(tags) + "\n" + extra_head + "  </head>", 1)
    if noscript:
        html = html.replace('<div id="root"></div>', f'<div id="root"></div>\n    <noscript>{noscript}</noscript>', 1)
    response = HttpResponse(html, status=status, content_type="text/html; charset=utf-8")
    if noindex:
        response["X-Robots-Tag"] = "noindex, nofollow"
    # Page HTML de la boutique : l'aperçu du thème l'affiche dans une iframe de la même origine.
    response["X-Frame-Options"] = "SAMEORIGIN"
    response["Content-Security-Policy"] = settings.STOREFRONT_CSP
    response["Cache-Control"] = "no-cache"
    return response


def home(request):
    base = site_url(request)
    org = {"@context": "https://schema.org", "@type": "OnlineStore", "name": settings.SITE_NAME, "url": f"{base}/"}
    return render(
        request,
        title=f"{settings.SITE_NAME} — soins coréens et naturels au Maroc",
        description=DEFAULT_DESCRIPTION,
        canonical=f"{base}/",
        extra_head="    " + json_ld(org) + "\n",
    )


def products(request):
    base = site_url(request)
    if request.GET.get("favoris"):
        return render(
            request, title=f"Mes favoris — {settings.SITE_NAME}", description=DEFAULT_DESCRIPTION, noindex=True
        )
    slug = request.GET.get("categorie")
    category = Category.objects.filter(slug=slug, is_active=True).first() if slug else None
    if slug and not category:
        return render(
            request,
            title=f"Catégorie introuvable — {settings.SITE_NAME}",
            description=DEFAULT_DESCRIPTION,
            noindex=True,
            status=404,
        )
    if category:
        return render(
            request,
            title=f"{category.name} — {settings.SITE_NAME}",
            description=(
                f"Nos soins coréens {category.name.lower()} : livraison partout au Maroc, paiement à la livraison."
            ),
            canonical=f"{base}/produits?categorie={category.slug}",
        )
    # Autres filtres (ingrédient…) : même contenu que la liste → URL canonique = la liste.
    return render(
        request,
        title=f"Nos produits — {settings.SITE_NAME}",
        description=DEFAULT_DESCRIPTION,
        canonical=f"{base}/produits",
    )


def product(request, slug):
    base = site_url(request)
    p = Product.objects.filter(slug=slug).first()
    if p is None or p.status == Product.Status.DRAFT:
        return render(
            request,
            title=f"Produit introuvable — {settings.SITE_NAME}",
            description=DEFAULT_DESCRIPTION,
            noindex=True,
            status=404,
        )
    if p.status == Product.Status.ARCHIVED:
        return render(
            request,
            title=f"Produit retiré — {settings.SITE_NAME}",
            description=DEFAULT_DESCRIPTION,
            noindex=True,
            status=410,
        )
    data = public.product_payload(public.public_products_queryset().get(pk=p.pk))
    url = f"{base}/produits/{p.slug}"
    image = absolute(base, data["seo"]["image"])
    in_stock = data["inStock"]
    offer = {
        "@type": "Offer",
        "url": url,
        "priceCurrency": "MAD",
        "price": f"{data['price']:.2f}",
        "availability": "https://schema.org/InStock" if in_stock else "https://schema.org/OutOfStock",
        "itemCondition": "https://schema.org/NewCondition",
    }
    ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": data["displayName"],
        "description": data["seo"]["description"],
        "brand": {"@type": "Brand", "name": data["brand"]},
        "url": url,
        "offers": offer,
    }
    if image:
        ld["image"] = [absolute(base, i["src"]) for i in data["galleryImages"]] or [image]
    sku = next((v["sku"] for v in data["variants"] if v["isDefault"] and v["sku"]), None)
    if sku:
        ld["sku"] = sku
    head = (
        "    " + json_ld(ld) + "\n" + f'    <meta property="product:price:amount" content="{data["price"]:.2f}" />\n'
        '    <meta property="product:price:currency" content="MAD" />\n'
    )
    noscript = (
        f"<h1>{escape(data['displayName'])}</h1><p>{escape(data['summary'])}</p>"
        f"<p>Prix : {data['price']:.2f} DH{'' if in_stock else ' — épuisé'}</p>"
    )
    return render(
        request,
        title=data["seo"]["title"] + f" — {settings.SITE_NAME}",
        description=data["seo"]["description"],
        canonical=url,
        image=image,
        og_type="product",
        extra_head=head,
        noscript=noscript,
    )


def private_page(request, *args, **kwargs):
    """Panier, commande, confirmation, administration : jamais indexés."""
    return render(request, title=settings.SITE_NAME, description=DEFAULT_DESCRIPTION, noindex=True)


def not_found(request, *args, **kwargs):
    return render(
        request,
        title=f"Page introuvable — {settings.SITE_NAME}",
        description=DEFAULT_DESCRIPTION,
        noindex=True,
        status=404,
    )


def robots_txt(request):
    base = site_url(request)
    lines = [
        "User-agent: *",
        "Allow: /",
        *[f"Disallow: {p}" for p in (*PRIVATE_PREFIXES, "/api/")],
        f"Sitemap: {base}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    base = site_url(request)
    urls = [(f"{base}/", None, []), (f"{base}/produits", None, [])]
    for c in Category.objects.filter(is_active=True, product_links__product__status=Product.Status.ACTIVE).distinct():
        urls.append((f"{base}/produits?categorie={c.slug}", None, []))
    for p in public.public_products_queryset():
        payload = public.product_payload(p)
        images = [absolute(base, i["src"]) for i in payload["galleryImages"]]
        urls.append((f"{base}/produits/{p.slug}", p.updated_at.date().isoformat(), images))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
    ]
    for loc, lastmod, images in urls:
        parts.append("  <url>")
        parts.append(f"    <loc>{xml_escape(loc)}</loc>")
        if lastmod:
            parts.append(f"    <lastmod>{lastmod}</lastmod>")
        parts += [f"    <image:image><image:loc>{xml_escape(i)}</image:loc></image:image>" for i in images]
        parts.append("  </url>")
    parts.append("</urlset>")
    return HttpResponse("\n".join(parts) + "\n", content_type="application/xml; charset=utf-8")
