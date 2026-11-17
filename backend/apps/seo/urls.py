"""Pages HTML de la boutique (référencement). À placer APRÈS /api/ et /media/ dans config/urls.py.

Français : adresses historiques (/, /produits…). Arabe : mêmes pages sous /ar (/ar, /ar/produits…).
"""

from django.urls import path, re_path

from . import views

AR = {"lang": "ar"}

urlpatterns = [
    path("robots.txt", views.robots_txt, name="robots"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap"),
    path("", views.home, name="seo-home"),
    path("produits", views.products, name="seo-products"),
    path("produits/<slug:slug>", views.product, name="seo-product"),
    path("collections/<slug:slug>", views.collection, name="seo-collection"),
    path("confidentialite", views.privacy, name="seo-privacy"),
    path("blog", views.blog, name="seo-blog"),
    path("blog/<slug:slug>", views.blog_article, name="seo-blog-article"),
    path("avis", views.reviews, name="seo-reviews"),
    # Arabe
    path("ar", views.home, AR, name="seo-home-ar"),
    path("ar/", views.home, AR),
    path("ar/produits", views.products, AR, name="seo-products-ar"),
    path("ar/produits/<slug:slug>", views.product, AR, name="seo-product-ar"),
    path("ar/collections/<slug:slug>", views.collection, AR, name="seo-collection-ar"),
    path("ar/confidentialite", views.privacy, AR, name="seo-privacy-ar"),
    path("ar/blog", views.blog, AR, name="seo-blog-ar"),
    path("ar/blog/<slug:slug>", views.blog_article, AR, name="seo-blog-article-ar"),
    path("ar/avis", views.reviews, AR, name="seo-reviews-ar"),
    re_path(r"^(ar/)?(panier|commande|confirmation)/?$", views.private_page),
    re_path(r"^admin(/.*)?$", views.private_page),
    re_path(r"^(?!api/|media/|static/|assets/).*$", views.not_found),
]
