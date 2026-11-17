from django.urls import path

from . import views
from .product_reviews import PublicProductReviewsView

urlpatterns = [
    path("reviews", views.PublicReviewsView.as_view(), name="store-reviews"),
    path("products/<slug:slug>/reviews", PublicProductReviewsView.as_view(), name="store-product-reviews"),
]
