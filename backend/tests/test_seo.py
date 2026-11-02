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
    assert h.count("<title>") == 1 and "<title>Crème test hydratante — Ma Petite Corée</title>" in h
    assert h.count('name="description"') == 1 and 'content="Une crème légère."' in h
    assert '<link rel="canonical" href="https://boutique.exemple.ma/produits/creme-test" />' in h
    assert (
        '<meta property="og:type" content="product" />' in h
        and 'og:image" content="https://boutique.exemple.ma/media/' in h
    )
    (product,) = ld(html)
    assert product["@type"] == "Product" and product["offers"]["price"] == "129.00"
    assert product["offers"]["priceCurrency"] == "MAD" and product["offers"]["availability"].endswith("InStock")
    assert "<noscript><h1>Marque Crème test</h1>" in html and "Prix : 129.00 DH" in html
    assert "noindex" not in h
    assert "script-src 'self'" in r["Content-Security-Policy"] and r["X-Frame-Options"] == "SAMEORIGIN"


@pytest.mark.django_db
def test_produit_epuise_reste_indexe_avec_disponibilite(client, sellable):
    sellable(slug="epuise", stock=0)
    r = client.get("/produits/epuise")
    assert r.status_code == 200 and ld(r.content.decode())[0]["offers"]["availability"].endswith("OutOfStock")
    assert "épuisé" in r.content.decode()


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
    assert "<title>Éclat — Ma Petite Corée</title>" in r.content.decode()
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


def test_csp_autorise_seulement_le_pixel_meta_sans_script_en_ligne(client):
    header = client.get("/panier")["Content-Security-Policy"]
    csp = dict(part.strip().split(" ", 1) for part in header.split(";") if part.strip())
    assert csp["script-src"] == "'self' https://connect.facebook.net"  # aucun 'unsafe-inline' ni autre domaine
    assert "https://www.facebook.com" in csp["connect-src"] and "https://www.facebook.com" in csp["img-src"]
    assert csp["object-src"] == "'none'" and csp["frame-ancestors"] == "'self'"
