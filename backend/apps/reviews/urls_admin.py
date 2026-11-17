from django.urls import path

from . import product_reviews, views

urlpatterns = [
    path("reviews", views.AdminReviewListView.as_view(), name="admin-reviews"),
    path("reviews/<int:pk>", views.AdminReviewDetailView.as_view(), name="admin-review"),
    path("product-reviews", product_reviews.AdminProductReviewListView.as_view(), name="admin-product-reviews"),
    path(
        "product-reviews/<int:pk>", product_reviews.AdminProductReviewDetailView.as_view(), name="admin-product-review"
    ),
]
