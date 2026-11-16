from django.urls import path

from . import views

urlpatterns = [
    path("reviews", views.AdminReviewListView.as_view(), name="admin-reviews"),
    path("reviews/<int:pk>", views.AdminReviewDetailView.as_view(), name="admin-review"),
]
