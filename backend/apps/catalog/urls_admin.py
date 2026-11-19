from django.urls import path

from apps.media_library import views as media_views

from . import collections_admin, filters_admin, views

urlpatterns = [
    path("categories", views.CategoryListCreateView.as_view(), name="admin-categories"),
    path("categories/reorder", views.CategoryReorderView.as_view(), name="admin-categories-reorder"),
    path("categories/<int:pk>", views.CategoryDetailView.as_view(), name="admin-category"),
    path("categories/<int:pk>/products", views.CategoryProductsView.as_view(), name="admin-category-products"),
    path("collections", collections_admin.CollectionListCreateView.as_view(), name="admin-collections"),
    path("collections/reorder", collections_admin.CollectionReorderView.as_view(), name="admin-collections-reorder"),
    path("collections/<int:pk>", collections_admin.CollectionDetailView.as_view(), name="admin-collection"),
    path(
        "collections/<int:pk>/products",
        collections_admin.CollectionProductsView.as_view(),
        name="admin-collection-products",
    ),
    path("filters", filters_admin.FilterGroupListCreateView.as_view(), name="admin-filters"),
    path("filters/reorder", filters_admin.FilterGroupReorderView.as_view(), name="admin-filters-reorder"),
    path("filters/<int:pk>", filters_admin.FilterGroupDetailView.as_view(), name="admin-filter-group"),
    path("filters/<int:pk>/options", filters_admin.FilterOptionCreateView.as_view(), name="admin-filter-options"),
    path(
        "filters/<int:pk>/options/reorder",
        filters_admin.FilterOptionReorderView.as_view(),
        name="admin-filter-options-reorder",
    ),
    path("filter-options/<int:pk>", filters_admin.FilterOptionDetailView.as_view(), name="admin-filter-option"),
    path("products/<int:pk>/filters", filters_admin.ProductFiltersView.as_view(), name="admin-product-filters"),
    path("products", views.ProductListCreateView.as_view(), name="admin-products"),
    path("products/quick-order", views.ProductQuickOrderBulkView.as_view(), name="admin-products-quick-order"),
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
    path(
        "products/<int:pk>/marketing-images",
        views.MarketingImageListCreateView.as_view(),
        name="admin-marketing-images",
    ),
    path(
        "products/<int:pk>/marketing-images/reorder",
        views.MarketingImageReorderView.as_view(),
        name="admin-marketing-reorder",
    ),
    path("marketing-images/<int:pk>", views.MarketingImageDetailView.as_view(), name="admin-marketing-image"),
    path("media", media_views.MediaListCreateView.as_view(), name="admin-media"),
    path("media/<int:pk>", media_views.MediaDetailView.as_view(), name="admin-media-detail"),
]
