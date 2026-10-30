"""API publique de la boutique — chemins identiques à src/api/endpoints.js (VITE_API_BASE_URL=/api/v1/store)."""

from django.urls import path

from . import views

urlpatterns = [
    path("products", views.PublicProductListView.as_view(), name="store-products"),
    path("products/<slug:slug>", views.PublicProductDetailView.as_view(), name="store-product"),
    path("categories", views.PublicCategoryListView.as_view(), name="store-categories"),
]
