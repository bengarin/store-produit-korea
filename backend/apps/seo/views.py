"""
Référencement : la boutique est une application React (une seule page HTML). Pour que Google, Bing, Facebook,
WhatsApp… reçoivent les VRAIES informations de chaque page SANS exécuter JavaScript, Django renvoie le index.html
construit par Vite (FRONTEND_DIST_DIR) en y injectant, selon l'URL :
- <title>, meta description, URL canonique, Open Graph / Twitter ;
- données structurées schema.org Product (prix, devise MAD, disponibilité) sur les fiches produit ;
- le CONTENU principal de la page en HTML dans <div id="root"> (apps/seo/content.py) : lisible sans JavaScript ;
- les données de démarrage de l'application (apps/seo/bootstrap.py) : premier affichage sans attendre l'API ;
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

from apps.blog.public import article_payload, published_articles
from apps.catalog import public
from apps.catalog.models import Category, Product
from apps.reviews.views import public_reviews

from . import content
from .bootstrap import data_script, store_data

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


# Titres et descriptions des pages, par langue (arabe : adresses /ar/…). [À VÉRIFIER] relecture arabophone.
PAGE_TEXTS = {
    "fr": {
        "home": f"{settings.SITE_NAME} — soins coréens et naturels au Maroc",
        "description": DEFAULT_DESCRIPTION,
        "products": "Nos produits",
        "favorites": "Mes favoris",
        "category_404": "Catégorie introuvable",
        "category_description": "Nos soins coréens {name} : livraison partout au Maroc, paiement à la livraison.",
        "product_404": "Produit introuvable",
        "product_410": "Produit retiré",
        "blog": "Blog",
        "blog_description": "Conseils de soin, routines et ingrédients coréens : le blog de Ma Petite Corée.",
        "article_404": "Article introuvable",
        "reviews": "Avis clients",
        "reviews_description": "Les avis de nos clientes et clients sur la boutique Ma Petite Corée.",
        "privacy": "Politique de confidentialité",
        "privacy_description": (
            "Données collectées, cookies, pixel Meta et consentement sur la boutique Ma Petite Corée."
        ),
        "not_found": "Page introuvable",
    },
    "ar": {
        "home": f"{settings.SITE_NAME} — منتجات عناية كورية وطبيعية في المغرب",
        "description": (
            f"{settings.SITE_NAME} — منتجات عناية كورية وطبيعية. التوصيل إلى جميع أنحاء المغرب، والدفع عند الاستلام."
        ),
        "products": "منتجاتنا",
        "favorites": "مفضلاتي",
        "category_404": "الفئة غير موجودة",
        "category_description": "منتجات العناية الكورية — {name}: التوصيل إلى جميع أنحاء المغرب، والدفع عند الاستلام.",
        "product_404": "المنتج غير موجود",
        "product_410": "المنتج لم يعد متوفرًا",
        "blog": "المدونة",
        "blog_description": "نصائح العناية والروتين والمكونات الكورية: مدونة Ma Petite Corée.",
        "article_404": "المقال غير موجود",
        "reviews": "آراء العملاء",
        "reviews_description": "آراء عملائنا حول متجر Ma Petite Corée.",
        "privacy": "سياسة الخصوصية",
        "privacy_description": "البيانات المجمعة وملفات تعريف الارتباط وبكسل Meta والموافقة في متجر Ma Petite Corée.",
        "not_found": "الصفحة غير موجودة",
    },
}
LANGS = ("fr", "ar")
OG_LOCALE = {"fr": "fr_MA", "ar": "ar_MA"}
HREFLANG = {"fr": "fr-MA", "ar": "ar-MA"}


def pt(lang: str, key: str) -> str:
    return PAGE_TEXTS[lang][key]


def lang_url(base: str, lang: str, path: str) -> str:
    """Adresse d'une page dans une langue : /produits → /ar/produits ; / → /ar."""
    if lang == "ar":
        return f"{base}/ar" if path == "/" else f"{base}/ar{path}"
    return f"{base}{path}"


def alternates(base: str, path: str) -> dict:
    return {lang: lang_url(base, lang, path) for lang in LANGS}


def request_lang(request) -> str:
    return "ar" if request.path == "/ar" or request.path.startswith("/ar/") else "fr"


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
    body="",
    data=None,
    status=200,
    lang="fr",
    alternate=None,
) -> HttpResponse:
    html = index_html()
    if lang == "ar":  # page arabe : langue et sens de lecture dès le HTML envoyé
        html = html.replace('<html lang="fr">', '<html lang="ar" dir="rtl">', 1)
    # Retire le titre et la description par défaut de index.html : remplacés par ceux de la page.
    html = re.sub(r"<title>.*?</title>", "", html, count=1, flags=re.S)
    html = re.sub(r'<meta name="description"[^>]*>', "", html, count=1)
    tags = [f"<title>{escape(title)}</title>", f'<meta name="description" content="{escape(description)}" />']
    if noindex:
        tags.append('<meta name="robots" content="noindex, nofollow" />')
    if canonical:
        tags.append(f'<link rel="canonical" href="{escape(canonical)}" />')
    # Versions française et arabe de la même page (hreflang), français par défaut.
    if alternate and not noindex:
        tags += [
            f'<link rel="alternate" hreflang="{HREFLANG[code]}" href="{escape(url)}" />'
            for code, url in alternate.items()
        ]
        tags.append(f'<link rel="alternate" hreflang="x-default" href="{escape(alternate["fr"])}" />')
    tags += [
        f'<meta property="og:site_name" content="{escape(settings.SITE_NAME)}" />',
        f'<meta property="og:title" content="{escape(title)}" />',
        f'<meta property="og:description" content="{escape(description)}" />',
        f'<meta property="og:type" content="{og_type}" />',
        f'<meta property="og:locale" content="{OG_LOCALE[lang]}" />',
        f'<meta property="og:locale:alternate" content="{OG_LOCALE["fr" if lang == "ar" else "ar"]}" />',
        f'<meta name="twitter:card" content="{"summary_large_image" if image else "summary"}" />',
    ]
    if canonical:
        tags.append(f'<meta property="og:url" content="{escape(canonical)}" />')
    if image:
        tags.append(f'<meta property="og:image" content="{escape(image)}" />')
    html = html.replace("</head>", "    " + "\n    ".join(tags) + "\n" + extra_head + "  </head>", 1)
    # Contenu lisible sans JavaScript (remplacé par l'application à son démarrage) + données de démarrage.
    root = f'<div id="root">{body}</div>' + (f"\n    {data_script(data)}" if data is not None else "")
    html = html.replace('<div id="root"></div>', root, 1)
    response = HttpResponse(html, status=status, content_type="text/html; charset=utf-8")
    if noindex:
        response["X-Robots-Tag"] = "noindex, nofollow"
    # Page HTML de la boutique : l'aperçu du thème l'affiche dans une iframe de la même origine.
    response["X-Frame-Options"] = "SAMEORIGIN"
    response["Content-Security-Policy"] = settings.STOREFRONT_CSP
    response["Cache-Control"] = "no-cache"
    return response


def _page(request, lang, path, *, title, description, **kwargs):
    """Page indexable : adresse canonique dans sa langue + versions fr/ar (hreflang)."""
    base = site_url(request)
    links = alternates(base, path)
    return render(
        request, title=title, description=description, canonical=links[lang], lang=lang, alternate=links, **kwargs
    )


def _missing(request, lang, key, status=404):
    title = f"{pt(lang, key)} — {settings.SITE_NAME}"
    return render(
        request, title=title, description=pt(lang, "description"), noindex=True, status=status, lang=lang,
        data=store_data(),
    )  # fmt: skip


def home(request, lang="fr"):
    base = site_url(request)
    org = {
        "@context": "https://schema.org",
        "@type": "OnlineStore",
        "name": settings.SITE_NAME,
        "url": lang_url(base, lang, "/"),
    }
    data = store_data()
    articles = [article_payload(a) for a in published_articles()[:3]]
    return _page(
        request,
        lang,
        "/",
        title=pt(lang, "home"),
        description=pt(lang, "description"),
        extra_head="    " + json_ld(org) + "\n",
        body=content.home(data["products"], data["categories"], articles, lang),
        data=data,
    )


def _in_category(products: list, categories: list, slug: str) -> list:
    """Produits d'une catégorie ET de ses sous-catégories (même règle que la boutique)."""
    family = {slug, *(c["id"] for c in categories if c.get("parent") == slug)}
    return [p for p in products if family.intersection(p.get("categories", []))]


def products(request, lang="fr"):
    data = store_data()
    if request.GET.get("favoris"):
        title = f"{pt(lang, 'favorites')} — {settings.SITE_NAME}"
        return render(request, title=title, description=pt(lang, "description"), noindex=True, data=data, lang=lang)
    slug = request.GET.get("categorie")
    category = next((c for c in data["categories"] if c["id"] == slug), None) if slug else None
    if slug and not category:
        return _missing(request, lang, "category_404")
    if category:
        name = content.localized(category, lang, "label")
        description = pt(lang, "category_description").format(name=name.lower() if lang == "fr" else name)
        items = _in_category(data["products"], data["categories"], slug)
        return _page(
            request,
            lang,
            f"/produits?categorie={slug}",
            title=f"{name} — {settings.SITE_NAME}",
            description=description,
            body=content.products_page(items, data["categories"], lang, name, description),
            data=data,
        )
    # Autres filtres (ingrédient, recherche, prix…) : même contenu que la liste → adresse canonique = la liste.
    return _page(
        request,
        lang,
        "/produits",
        title=f"{pt(lang, 'products')} — {settings.SITE_NAME}",
        description=pt(lang, "description"),
        body=content.products_page(
            data["products"], data["categories"], lang, pt(lang, "products"), pt(lang, "description")
        ),
        data=data,
    )


def product(request, slug, lang="fr"):
    p = Product.objects.filter(slug=slug).first()
    if p is None or p.status == Product.Status.DRAFT:
        return _missing(request, lang, "product_404")
    if p.status == Product.Status.ARCHIVED:
        return _missing(request, lang, "product_410", status=410)
    base = site_url(request)
    store = store_data()
    # Le produit actif est déjà dans les données de démarrage (même format que l'API).
    data = next(x for x in store["products"] if x["slug"] == p.slug)
    url = lang_url(base, lang, f"/produits/{p.slug}")
    image = absolute(base, data["seo"]["image"])
    in_stock = data["inStock"]
    if lang == "ar":
        ar = (data.get("translations") or {}).get("ar", {})
        name = ar.get("displayName") or data["displayName"]
        title = ar.get("displayName") or data["seo"]["title"]
        description = (ar.get("summary") or ar.get("cardLine") or data["seo"]["description"])[:300]
    else:
        name, title, description = data["displayName"], data["seo"]["title"], data["seo"]["description"]
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
        "name": name,
        "description": description,
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
    return _page(
        request,
        lang,
        f"/produits/{p.slug}",
        title=f"{title} — {settings.SITE_NAME}",
        description=description,
        image=image,
        og_type="product",
        extra_head=head,
        body=content.product_page(data, store["categories"], lang),
        data=store,
    )


def blog(request, lang="fr"):
    data = store_data()
    return _page(
        request,
        lang,
        "/blog",
        title=f"{pt(lang, 'blog')} — {settings.SITE_NAME}",
        description=pt(lang, "blog_description"),
        body=content.blog_page([article_payload(a) for a in published_articles()], data["categories"], lang),
        data=data,
    )


def blog_article(request, slug, lang="fr"):
    article = published_articles().filter(slug=slug).first()
    if article is None:
        return _missing(request, lang, "article_404")
    base = site_url(request)
    data = article_payload(article, full=True)
    store = store_data()
    url = lang_url(base, lang, f"/blog/{article.slug}")
    image = absolute(base, data["cover"]["src"]) if data["cover"] else None
    headline = content.localized(data, lang, "title")
    description = (content.localized(data, lang, "excerpt") or pt(lang, "description"))[:300]
    ld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": headline,
        "description": description,
        "inLanguage": lang,
        "datePublished": data["publishedAt"],
        "dateModified": article.updated_at.isoformat(),
        "url": url,
        "publisher": {"@type": "Organization", "name": settings.SITE_NAME},
    }
    if image:
        ld["image"] = [image]
    return _page(
        request,
        lang,
        f"/blog/{article.slug}",
        title=f"{headline} — {settings.SITE_NAME}",
        description=description,
        image=image,
        og_type="article",
        extra_head="    " + json_ld(ld) + "\n",
        body=content.article_page(data, store["categories"], lang),
        data=store,
    )


def reviews(request, lang="fr"):
    data = store_data()
    return _page(
        request,
        lang,
        "/avis",
        title=f"{pt(lang, 'reviews')} — {settings.SITE_NAME}",
        description=pt(lang, "reviews_description"),
        body=content.reviews_page(public_reviews(), data["categories"], lang),
        data=data,
    )


def private_page(request, *args, **kwargs):
    """Panier, commande, confirmation, administration : jamais indexés. Données de démarrage : boutique seulement."""
    lang = request_lang(request)
    data = None if request.path.startswith("/admin") else store_data()
    title = settings.SITE_NAME
    return render(request, title=title, description=pt(lang, "description"), noindex=True, data=data, lang=lang)


def privacy(request, lang="fr"):
    """Politique de confidentialité : non indexée tant que le texte n'a pas été validé juridiquement."""
    return render(
        request,
        title=f"{pt(lang, 'privacy')} — {settings.SITE_NAME}",
        description=pt(lang, "privacy_description"),
        canonical=lang_url(site_url(request), lang, "/confidentialite"),
        noindex=True,
        data=store_data(),
        lang=lang,
    )


def not_found(request, *args, **kwargs):
    return _missing(request, request_lang(request), "not_found")


def robots_txt(request):
    base = site_url(request)
    private = [*PRIVATE_PREFIXES, *(f"/ar{p}" for p in PRIVATE_PREFIXES if p != "/admin"), "/api/"]
    lines = ["User-agent: *", "Allow: /", *[f"Disallow: {p}" for p in private], f"Sitemap: {base}/sitemap.xml"]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    """Chaque page en français ET en arabe, avec les liens entre les deux versions (hreflang)."""
    base = site_url(request)
    pages = [(path, None, []) for path in ("/", "/produits", "/blog", "/avis")]
    for a in published_articles():
        cover = [absolute(base, a.cover.url)] if a.cover_id else []
        pages.append((f"/blog/{a.slug}", a.updated_at.date().isoformat(), cover))
    for c in Category.objects.filter(
        public.VISIBLE_CATEGORY, product_links__product__status=Product.Status.ACTIVE
    ).distinct():
        pages.append((f"/produits?categorie={c.slug}", None, []))
    for p in public.public_products_queryset():
        payload = public.product_payload(p)
        images = [absolute(base, i["src"]) for i in payload["galleryImages"]]
        pages.append((f"/produits/{p.slug}", p.updated_at.date().isoformat(), images))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
        ' xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"'
        ' xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for path, lastmod, images in pages:
        links = alternates(base, path)
        for lang in LANGS:
            parts.append("  <url>")
            parts.append(f"    <loc>{xml_escape(links[lang])}</loc>")
            parts += [
                f'    <xhtml:link rel="alternate" hreflang="{HREFLANG[code]}" href="{xml_escape(url)}" />'
                for code, url in links.items()
            ]
            parts.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{xml_escape(links["fr"])}" />')
            if lastmod:
                parts.append(f"    <lastmod>{lastmod}</lastmod>")
            parts += [f"    <image:image><image:loc>{xml_escape(i)}</image:loc></image:image>" for i in images]
            parts.append("  </url>")
    parts.append("</urlset>")
    return HttpResponse("\n".join(parts) + "\n", content_type="application/xml; charset=utf-8")
