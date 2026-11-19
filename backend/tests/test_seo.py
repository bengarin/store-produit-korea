"""Phase 7 — référencement : HTML réellement reçu par un robot (sans JavaScript), sitemap, robots."""

import json
import re
from xml.etree import ElementTree

import pytest
from django.test import override_settings

from apps.catalog.models import Product, Variant

INDEX = """<!doctype html>
<html lang="fr">
  <head>
    <meta charset="UTF-8" />
    <meta name="description" content="Description par défaut" />
    <title>Titre par défaut</title>
    <script type="module" crossorigin src="/assets/index-abc.js"></script>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
"""


@pytest.fixture(autouse=True)
def _front_construit(tmp_path):
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    with override_settings(FRONTEND_DIST_DIR=tmp_path, SITE_URL="https://boutique.exemple.ma"):
        yield


def head(html):
    return html.split("</head>")[0]


def ld(html):
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    return [json.loads(b) for b in blocks]


@pytest.mark.django_db
def test_fiche_produit_html_complet_sans_javascript(client, sellable):
    p = sellable(slug="creme-test", stock=5, price="129.00")
    Product.objects.filter(pk=p.pk).update(seo_title="Crème test hydratante", seo_description="Une crème légère.")
    r = client.get("/produits/creme-test", HTTP_USER_AGENT="Googlebot/2.1")
    html = r.content.decode()
    assert r.status_code == 200 and r["Content-Type"].startswith("text/html")
    h = head(html)
    assert h.count("<title>") == 1 and "<title>Crème test hydratante — Jodhur</title>" in h
    assert h.count('name="description"') == 1 and 'content="Une crème légère."' in h
    assert '<link rel="canonical" href="https://boutique.exemple.ma/produits/creme-test" />' in h
    assert (
        '<meta property="og:type" content="product" />' in h
        and 'og:image" content="https://boutique.exemple.ma/media/' in h
    )
    (product,) = ld(html)
    assert product["@type"] == "Product" and product["offers"]["price"] == "129.00"
    assert product["offers"]["priceCurrency"] == "MAD" and product["offers"]["availability"].endswith("InStock")
    # Contenu lisible sans JavaScript, dans <div id="root"> (remplacé par l'application à son démarrage).
    root = html.split('<div id="root">')[1].split('<script id="mpc-data"')[0]
    assert "<h1>Marque Crème test</h1>" in root and "Prix : 129 DH · Disponible" in root
    assert "noindex" not in h
    assert "script-src 'self'" in r["Content-Security-Policy"] and r["X-Frame-Options"] == "SAMEORIGIN"


@pytest.mark.django_db
def test_produit_epuise_reste_indexe_avec_disponibilite(client, sellable):
    sellable(slug="epuise", stock=0)
    r = client.get("/produits/epuise")
    assert r.status_code == 200 and ld(r.content.decode())[0]["offers"]["availability"].endswith("OutOfStock")
    assert "épuisé" in r.content.decode().lower()


@pytest.mark.django_db
def test_archive_410_brouillon_et_inconnu_404_jamais_indexes(client, product):
    product(slug="archive", status="archived")
    product(slug="brouillon", status="draft")
    for url, code in (
        ("/produits/archive", 410),
        ("/produits/brouillon", 404),
        ("/produits/inconnu", 404),
        ("/nimporte-quoi", 404),
    ):
        r = client.get(url)
        assert r.status_code == code, url
        assert (
            'name="robots" content="noindex, nofollow"' in r.content.decode()
            and r["X-Robots-Tag"] == "noindex, nofollow"
        )
        assert "Brouillon" not in r.content.decode()  # rien du brouillon n'est divulgué


@pytest.mark.django_db
def test_nom_de_produit_piege_ne_casse_pas_la_page(client, sellable):
    p = sellable(slug="piege", stock=5)
    Product.objects.filter(pk=p.pk).update(
        display_name='</script><script>alert(1)</script>"><img src=x onerror=alert(2)>'
    )
    html = client.get("/produits/piege").content.decode()
    assert "<script>alert(1)" not in html and "<img src=x" not in html
    assert ld(html)[0]["name"].startswith("</script>")  # le JSON reste valide et contient le texte exact


@pytest.mark.django_db
def test_pages_privees_et_favoris_non_indexees(client):
    for url in ("/panier", "/commande", "/confirmation", "/admin/orders", "/admin/theme", "/produits?favoris=1"):
        r = client.get(url)
        assert r.status_code == 200 and r["X-Robots-Tag"] == "noindex, nofollow", url


@pytest.mark.django_db
def test_categorie_canonique_et_inconnue(client, category):
    category(slug="eclat", name="Éclat")
    r = client.get("/produits?categorie=eclat")
    assert "<title>Éclat — Jodhur</title>" in r.content.decode()
    assert 'href="https://boutique.exemple.ma/produits?categorie=eclat"' in r.content.decode()
    assert client.get("/produits?categorie=fantome").status_code == 404
    other = client.get("/produits?ingredient=aloe").content.decode()
    assert 'href="https://boutique.exemple.ma/produits"' in other  # filtres secondaires : canonique = liste


@pytest.mark.django_db
def test_sitemap_et_robots(client, sellable, product):
    sellable(slug="visible", stock=5)
    product(slug="cache-brouillon", status="draft")
    product(slug="cache-archive", status="archived")
    xml = client.get("/sitemap.xml")
    assert xml["Content-Type"].startswith("application/xml")
    tree = ElementTree.fromstring(xml.content)  # noqa: S314 - XML produit par notre propre serveur
    locs = [e.text for e in tree.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    assert "https://boutique.exemple.ma/produits/visible" in locs
    assert not any("cache-" in loc for loc in locs)
    robots = client.get("/robots.txt").content.decode()
    assert "Disallow: /admin" in robots and "Disallow: /api/" in robots
    assert "Sitemap: https://boutique.exemple.ma/sitemap.xml" in robots


@pytest.mark.django_db
def test_api_inconnue_reste_en_json(client):
    r = client.get("/api/v1/store/inexistant")
    assert r.status_code == 404 and r["Content-Type"].startswith("application/json")


@pytest.mark.django_db
def test_variante_par_defaut_et_sku(client, sellable):
    p = sellable(slug="avec-sku", stock=5)
    Variant.objects.filter(product=p).update(sku="MPC-001")
    assert ld(client.get("/produits/avec-sku").content.decode())[0]["sku"] == "MPC-001"


@pytest.mark.django_db
def test_csp_autorise_seulement_le_pixel_meta_sans_script_en_ligne(client):
    header = client.get("/panier")["Content-Security-Policy"]
    csp = dict(part.strip().split(" ", 1) for part in header.split(";") if part.strip())
    assert csp["script-src"] == "'self' https://connect.facebook.net"  # aucun 'unsafe-inline' ni autre domaine
    assert "https://www.facebook.com" in csp["connect-src"] and "https://www.facebook.com" in csp["img-src"]
    assert csp["object-src"] == "'none'" and csp["frame-ancestors"] == "'self'"


@pytest.mark.django_db
def test_politique_de_confidentialite_servie_mais_non_indexee(client):
    r = client.get("/confidentialite")
    html = r.content.decode()
    assert r.status_code == 200 and "<title>Politique de confidentialité — Jodhur</title>" in html
    assert r["X-Robots-Tag"] == "noindex, nofollow"  # pas d'indexation tant que le texte n'est pas validé
    assert "/confidentialite" not in client.get("/sitemap.xml").content.decode()


@pytest.mark.django_db
def test_blog_et_avis_html_et_sitemap(client):
    from django.utils import timezone

    from apps.blog.models import Article

    Article.objects.create(
        title="Routine <coréenne>", slug="routine", excerpt="Les bases.", body="<p>x</p>",
        status="published", published_at=timezone.now(),
    )  # fmt: skip
    Article.objects.create(title="Brouillon", slug="brouillon", body="<p>x</p>")
    html = client.get("/blog/routine").content.decode()
    assert "<title>Routine &lt;coréenne&gt; — " in html and '"@type": "BlogPosting"' in html
    assert 'rel="canonical" href="https://boutique.exemple.ma/blog/routine"' in html
    assert client.get("/blog/brouillon").status_code == 404
    assert client.get("/blog").status_code == client.get("/avis").status_code == 200
    sitemap = client.get("/sitemap.xml").content.decode()
    assert "/blog/routine</loc>" in sitemap and "/blog/brouillon" not in sitemap and "/avis</loc>" in sitemap


@pytest.mark.django_db
def test_contenu_html_et_donnees_de_demarrage(client, sellable, category):
    """G2 : contenu lisible sans JavaScript ; P1 : données de l'application jointes à la page (mêmes que l'API)."""
    sellable(slug="creme-test", stock=5, price="129.00")
    html = client.get("/").content.decode()
    root = html.split('<div id="root">')[1].split('<script id="mpc-data"')[0]
    assert '<a href="/produits/creme-test">' in root and "129 DH" in root and "<h1>" in root
    assert '<a href="/produits?categorie=hydratation">Hydratation</a>' in root  # liens vers les catégories
    data = json.loads(re.search(r'<script id="mpc-data" type="application/json">(.*?)</script>', html, re.S).group(1))
    assert set(data) == {"products", "categories", "filters", "collections", "config", "theme"}
    assert data["products"] == client.get("/api/v1/store/products").json()["items"]
    assert data["categories"] == client.get("/api/v1/store/categories").json()["items"]
    assert data["config"] == client.get("/api/v1/store/config").json()
    assert "promoCodes" not in data["config"]  # jamais les codes promo
    cat = client.get("/produits?categorie=cat-creme-test").content.decode()  # catégorie du produit de test
    assert "<h1>Cat creme-test</h1>" in cat and "/produits/creme-test" in cat
    assert (
        "/produits/creme-test"
        not in client.get("/produits?categorie=hydratation").content.decode().split("mpc-data")[0]
    )
    # Administration : ni contenu ni données de la boutique.
    admin = client.get("/admin/orders").content.decode()
    assert 'id="mpc-data"' not in admin and '<div id="root"></div>' in admin


@pytest.mark.django_db
def test_donnees_de_demarrage_ne_peuvent_pas_fermer_la_balise(client, sellable):
    p = sellable(slug="piege2", stock=5)
    Product.objects.filter(pk=p.pk).update(display_name="</script><script>alert(1)</script>")
    html = client.get("/produits").content.decode()
    block = re.search(r'<script id="mpc-data" type="application/json">(.*?)</script>', html, re.S).group(1)
    assert "</script>" not in block and "<script>alert(1)" not in html
    assert json.loads(block)["products"][0]["displayName"] == "</script><script>alert(1)</script>"


@pytest.mark.django_db
def test_pages_arabes_indexables_avec_hreflang(client, sellable):
    """G1 : chaque page existe en arabe sous /ar, avec langue, sens, canonique et liens fr/ar (hreflang)."""
    p = sellable(slug="creme-test", stock=5, price="129.00")
    Product.objects.filter(pk=p.pk).update(display_name_ar="كريم تجريبي", summary_ar="ملخص بالعربية")
    base = "https://boutique.exemple.ma"
    r = client.get("/ar/produits/creme-test")
    html = r.content.decode()
    assert r.status_code == 200 and '<html lang="ar" dir="rtl">' in html
    h = head(html)
    assert "<title>كريم تجريبي — Jodhur</title>" in h and 'content="ملخص بالعربية"' in h
    assert f'<link rel="canonical" href="{base}/ar/produits/creme-test" />' in h
    assert f'hreflang="fr-MA" href="{base}/produits/creme-test"' in h
    assert f'hreflang="ar-MA" href="{base}/ar/produits/creme-test"' in h
    assert f'hreflang="x-default" href="{base}/produits/creme-test"' in h
    assert '<meta property="og:locale" content="ar_MA" />' in h
    assert ld(html)[0]["name"] == "كريم تجريبي" and ld(html)[0]["url"] == f"{base}/ar/produits/creme-test"
    root = html.split('<div id="root">')[1].split('<script id="mpc-data"')[0]
    assert "<h1>كريم تجريبي</h1>" in root and 'href="/ar/produits"' in root and "129 درهم" in root
    # Version française : inchangée, avec les mêmes liens fr/ar.
    fr = client.get("/produits/creme-test").content.decode()
    assert '<html lang="fr">' in fr and f'hreflang="ar-MA" href="{base}/ar/produits/creme-test"' in fr
    # Toutes les pages publiques existent en arabe.
    for url in ("/ar", "/ar/produits", "/ar/blog", "/ar/avis", "/ar/confidentialite"):
        page = client.get(url)
        assert page.status_code == 200 and '<html lang="ar" dir="rtl">' in page.content.decode(), url
    assert client.get("/ar/produits/inconnu").status_code == 404
    missing = client.get("/ar/nexiste-pas")
    assert missing.status_code == 404 and '<html lang="ar" dir="rtl">' in missing.content.decode()
    # Pages privées en arabe : jamais indexées, sans hreflang.
    cart = client.get("/ar/panier")
    assert cart["X-Robots-Tag"] == "noindex, nofollow" and "hreflang" not in cart.content.decode()


@pytest.mark.django_db
def test_sitemap_et_robots_bilingues(client, sellable):
    sellable(slug="creme-test", stock=5)
    sitemap = client.get("/sitemap.xml").content.decode()
    tree = ElementTree.fromstring(sitemap)  # noqa: S314 - XML produit par notre propre serveur
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}
    locs = [u.find("s:loc", ns).text for u in tree.findall("s:url", ns)]
    base = "https://boutique.exemple.ma"
    assert f"{base}/produits/creme-test" in locs and f"{base}/ar/produits/creme-test" in locs
    assert f"{base}/" in locs and f"{base}/ar" in locs
    entry = next(u for u in tree.findall("s:url", ns) if u.find("s:loc", ns).text == f"{base}/ar/produits/creme-test")
    links = {link.get("hreflang"): link.get("href") for link in entry.findall("x:link", ns)}
    assert links == {
        "fr-MA": f"{base}/produits/creme-test",
        "ar-MA": f"{base}/ar/produits/creme-test",
        "x-default": f"{base}/produits/creme-test",
    }
    robots = client.get("/robots.txt").content.decode()
    assert "Disallow: /ar/panier" in robots and "Disallow: /panier" in robots and "Disallow: /ar/admin" not in robots
