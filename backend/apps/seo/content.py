"""
Contenu HTML des pages de la boutique, écrit par le serveur dans <div id="root"> (G2 de l'audit) :
les robots qui n'exécutent pas JavaScript (moteurs de recherche, moteurs de réponse IA, aperçus de liens) lisent
le vrai contenu — titres, produits, prix, liens, articles, avis. Dès que l'application React démarre, elle
remplace ce contenu par la page habituelle (même information, mise en page complète).

Tout texte venant de la base est échappé ; le HTML riche (descriptions, articles) est re-nettoyé (nh3).
`lang` : « fr » (adresses actuelles) ou « ar » (adresses /ar/…).
"""

from django.conf import settings
from django.utils.html import escape

from apps.core.html import sanitize_html

TEXTS = {
    "fr": {
        "home": "Accueil",
        "products": "Nos produits",
        "blog": "Blog",
        "reviews": "Avis clients",
        "privacy": "Politique de confidentialité",
        "tagline": "Soins coréens et naturels au Maroc",
        "intro": "Livraison partout au Maroc, paiement à la livraison.",
        "categories": "Catégories",
        "all_products": "Tous les produits",
        "latest_posts": "Derniers articles",
        "price": "Prix",
        "in_stock": "Disponible",
        "out_of_stock": "Épuisé",
        "ingredients": "Ingrédients",
        "usage": "Utilisation",
        "benefits": "Bienfaits",
        "skin_types": "Types de peau",
        "brand": "Marque",
        "read_more": "Lire l'article",
        "no_reviews": "Aucun avis publié pour le moment.",
        "average": "Note moyenne",
        "out_of": "sur 5",
        "reviews_count": "avis",
        "currency": "DH",
        "nav": "Navigation principale",
        "breadcrumb": "Fil d'Ariane",
    },
    "ar": {
        "home": "الرئيسية",
        "products": "منتجاتنا",
        "blog": "المدونة",
        "reviews": "آراء العملاء",
        "privacy": "سياسة الخصوصية",
        "tagline": "منتجات عناية كورية وطبيعية في المغرب",
        "intro": "التوصيل إلى جميع أنحاء المغرب، والدفع عند الاستلام.",
        "categories": "الفئات",
        "all_products": "جميع المنتجات",
        "latest_posts": "أحدث المقالات",
        "price": "السعر",
        "in_stock": "متوفر",
        "out_of_stock": "نفد من المخزون",
        "ingredients": "المكونات",
        "usage": "طريقة الاستعمال",
        "benefits": "الفوائد",
        "skin_types": "أنواع البشرة",
        "brand": "العلامة التجارية",
        "read_more": "قراءة المقال",
        "no_reviews": "لا توجد آراء منشورة حاليًا.",
        "average": "التقييم المتوسط",
        "out_of": "من 5",
        "reviews_count": "رأي",
        "currency": "درهم",
        "nav": "التنقل الرئيسي",
        "breadcrumb": "مسار التنقل",
    },
}


def t(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS["fr"])[key]


def prefix(lang: str) -> str:
    """Préfixe des adresses : « » en français, « /ar » en arabe."""
    return "/ar" if lang == "ar" else ""


def localized(item: dict, lang: str, key: str):
    """Champ dans la langue demandée ; champ arabe vide = texte français (comme dans la boutique)."""
    if lang == "ar":
        value = (item.get("translations") or {}).get("ar", {}).get(key)
        if value:
            return value
    return item.get(key)


def price(value, lang: str) -> str:
    if value is None:
        return ""
    text = f"{value:,.2f}".replace(",", " ").replace(".00", "")
    return f"{text} {t(lang, 'currency')}"


def _link(href: str, label: str) -> str:
    return f'<a href="{escape(href)}">{escape(label)}</a>'


def header(categories: list, lang: str) -> str:
    p = prefix(lang)
    tops = [c for c in categories if not c.get("parent")]
    links = [
        _link(f"{p}/", t(lang, "home")),
        _link(f"{p}/produits", t(lang, "products")),
        *[_link(f"{p}/produits?categorie={c['id']}", localized(c, lang, "label")) for c in tops],
        _link(f"{p}/blog", t(lang, "blog")),
        _link(f"{p}/avis", t(lang, "reviews")),
    ]
    return (
        f'<header class="ssr-header"><a class="ssr-brand" href="{p}/">{escape(settings.SITE_NAME)}</a>'
        f'<nav aria-label="{escape(t(lang, "nav"))}">{"".join(links)}</nav></header>'
    )


def footer(lang: str) -> str:
    p = prefix(lang)
    links = [_link(f"{p}/avis", t(lang, "reviews")), _link(f"{p}/blog", t(lang, "blog"))]
    links.append(_link(f"{p}/confidentialite", t(lang, "privacy")))
    return f'<footer class="ssr-footer"><p>{escape(t(lang, "intro"))}</p><nav>{"".join(links)}</nav></footer>'


def page(body: str, categories: list, lang: str) -> str:
    return f'<div class="ssr">{header(categories, lang)}<main class="ssr-main">{body}</main>{footer(lang)}</div>'


def product_list(products: list, lang: str) -> str:
    if not products:
        return ""
    p = prefix(lang)
    items = []
    for prod in products:
        name = localized(prod, lang, "displayName")
        line = localized(prod, lang, "cardLine") or ""
        stock = t(lang, "in_stock") if prod.get("inStock") else t(lang, "out_of_stock")
        items.append(
            f'<li><a href="{p}/produits/{escape(prod["slug"])}">{escape(name)}</a>'
            + (f"<p>{escape(line)}</p>" if line else "")
            + f"<p>{escape(price(prod.get('price'), lang))} · {escape(stock)}</p></li>"
        )
    return f'<ul class="ssr-products">{"".join(items)}</ul>'


def home(products: list, categories: list, articles: list, lang: str) -> str:
    p = prefix(lang)
    body = f"<h1>{escape(settings.SITE_NAME)} — {escape(t(lang, 'tagline'))}</h1><p>{escape(t(lang, 'intro'))}</p>"
    body += f"<h2>{escape(t(lang, 'products'))}</h2>" + product_list(products, lang)
    if articles:
        links = (_link(p + "/blog/" + a["slug"], localized(a, lang, "title")) for a in articles[:3])
        posts = "".join(f"<li>{link}</li>" for link in links)
        body += f"<h2>{escape(t(lang, 'latest_posts'))}</h2><ul>{posts}</ul>"
    return page(body, categories, lang)


def products_page(products: list, categories: list, lang: str, heading: str, intro: str = "") -> str:
    body = f"<h1>{escape(heading)}</h1>" + (f"<p>{escape(intro)}</p>" if intro else "")
    return page(body + product_list(products, lang), categories, lang)


def _list(title: str, values) -> str:
    values = [v for v in (values or []) if v]
    if not values:
        return ""
    items = "".join(f"<li>{escape(v if isinstance(v, str) else v.get('label', ''))}</li>" for v in values)
    return f"<h2>{escape(title)}</h2><ul>{items}</ul>"


def product_page(prod: dict, categories: list, lang: str) -> str:
    p = prefix(lang)
    name = localized(prod, lang, "displayName")
    by_id = {c["id"]: c for c in categories}
    crumbs = [_link(f"{p}/", t(lang, "home")), _link(f"{p}/produits", t(lang, "products"))]
    first = next((by_id[c] for c in prod.get("categories", []) if c in by_id), None)
    if first:
        crumbs.append(_link(f"{p}/produits?categorie={first['id']}", localized(first, lang, "label")))
    stock = t(lang, "in_stock") if prod.get("inStock") else t(lang, "out_of_stock")
    body = f'<nav class="ssr-crumbs" aria-label="{escape(t(lang, "breadcrumb"))}">{" › ".join(crumbs)}</nav>'
    body += f"<article><h1>{escape(name)}</h1>"
    body += f"<p>{escape(t(lang, 'brand'))} : {escape(prod.get('brand') or '')}</p>"
    body += f"<p>{escape(t(lang, 'price'))} : {escape(price(prod.get('price'), lang))} · {escape(stock)}</p>"
    summary = localized(prod, lang, "summary")
    if summary:
        body += f"<p>{escape(summary)}</p>"
    description = localized(prod, lang, "descriptionHtml")
    if description:
        body += f'<div class="ssr-rich">{sanitize_html(description)}</div>'
    body += _list(t(lang, "benefits"), localized(prod, lang, "benefits"))
    body += _list(t(lang, "ingredients"), localized(prod, lang, "ingredients"))
    body += _list(t(lang, "usage"), localized(prod, lang, "usage"))
    skin = localized(prod, lang, "skinTypes")
    if skin:
        body += f"<h2>{escape(t(lang, 'skin_types'))}</h2><p>{escape(skin)}</p>"
    return page(body + "</article>", categories, lang)


def blog_page(articles: list, categories: list, lang: str) -> str:
    p = prefix(lang)
    items = []
    for a in articles:
        title = localized(a, lang, "title")
        excerpt = localized(a, lang, "excerpt") or ""
        date = (a.get("publishedAt") or "")[:10]
        items.append(
            f"<li><h2>{_link(p + '/blog/' + a['slug'], title)}</h2>"
            + (f'<p><time datetime="{escape(date)}">{escape(date)}</time></p>' if date else "")
            + (f"<p>{escape(excerpt)}</p>" if excerpt else "")
            + "</li>"
        )
    body = f"<h1>{escape(t(lang, 'blog'))}</h1>" + (f'<ul class="ssr-posts">{"".join(items)}</ul>' if items else "")
    return page(body, categories, lang)


def article_page(article: dict, categories: list, lang: str) -> str:
    p = prefix(lang)
    title = localized(article, lang, "title")
    date = (article.get("publishedAt") or "")[:10]
    body = f'<nav class="ssr-crumbs">{_link(f"{p}/blog", t(lang, "blog"))}</nav><article><h1>{escape(title)}</h1>'
    if date:
        body += f'<p><time datetime="{escape(date)}">{escape(date)}</time></p>'
    excerpt = localized(article, lang, "excerpt")
    if excerpt:
        body += f"<p>{escape(excerpt)}</p>"
    html = localized(article, lang, "bodyHtml")
    if html:
        body += f'<div class="ssr-rich">{sanitize_html(html)}</div>'
    return page(body + "</article>", categories, lang)


def reviews_page(data: dict, categories: list, lang: str) -> str:
    body = f"<h1>{escape(t(lang, 'reviews'))}</h1>"
    if data["count"]:
        body += (
            f"<p>{escape(t(lang, 'average'))} : {data['average']} {escape(t(lang, 'out_of'))}"
            f" · {data['count']} {escape(t(lang, 'reviews_count'))}</p>"
        )
        items = "".join(
            f"<li><p><strong>{escape(r['name'])}</strong> · {r['rating']}/5 · "
            f'<time datetime="{escape(r["date"][:10])}">{escape(r["date"][:10])}</time></p>'
            f"<p>{escape(r['text'])}</p></li>"
            for r in data["items"]
        )
        body += f'<ul class="ssr-reviews">{items}</ul>'
    else:
        body += f"<p>{escape(t(lang, 'no_reviews'))}</p>"
    return page(body, categories, lang)
