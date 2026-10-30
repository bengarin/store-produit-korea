from django.urls import path

from apps.media_library import views as media_views

from . import views

urlpatterns = [
    path("categories", views.CategoryListCreateView.as_view(), name="admin-categories"),
    path("categories/reorder", views.CategoryReorderView.as_view(), name="admin-categories-reorder"),
    path("categories/<int:pk>", views.CategoryDetailView.as_view(), name="admin-category"),
    path("products", views.ProductListCreateView.as_view(), name="admin-products"),
    path("products/<int:pk>", views.ProductDetailView.as_view(), name="admin-product"),
    path("products/<int:pk>/status", views.ProductStatusView.as_view(), name="admin-product-status"),
    path("products/<int:pk>/preview", views.ProductPreviewView.as_view(), name="admin-product-preview"),
    path("products/<int:pk>/duplicate", views.ProductDuplicateView.as_view(), name="admin-product-duplicate"),
    path("products/<int:pk>/options", views.ProductOptionsView.as_view(), name="admin-product-options"),
    path("products/<int:pk>/variants", views.VariantListCreateView.as_view(), name="admin-product-variants"),
    path("variants/<int:pk>", views.VariantDetailView.as_view(), name="admin-variant"),
    path("products/<int:pk>/images", views.ProductImageListCreateView.as_view(), name="admin-product-images"),
    path("products/<int:pk>/images/reorder", views.ProductImageReorderView.as_view(), name="admin-images-reorder"),
    path("product-images/<int:pk>", views.ProductImageDetailView.as_view(), name="admin-product-image"),
    path("media", media_views.MediaListCreateView.as_view(), name="admin-media"),
    path("media/<int:pk>", media_views.MediaDetailView.as_view(), name="admin-media-detail"),
]
