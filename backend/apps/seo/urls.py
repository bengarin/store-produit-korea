"""Pages HTML de la boutique (référencement). À placer APRÈS /api/ et /media/ dans config/urls.py."""

from django.urls import path, re_path

from . import views

urlpatterns = [
    path("robots.txt", views.robots_txt, name="robots"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap"),
    path("", views.home, name="seo-home"),
    path("produits", views.products, name="seo-products"),
    path("produits/<slug:slug>", views.product, name="seo-product"),
    path("confidentialite", views.privacy, name="seo-privacy"),
    re_path(r"^(panier|commande|confirmation)/?$", views.private_page),
    re_path(r"^admin(/.*)?$", views.private_page),
    re_path(r"^(?!api/|media/|static/|assets/).*$", views.not_found),
]
