from django.urls import path

from . import views

urlpatterns = [path("reviews", views.PublicReviewsView.as_view(), name="store-reviews")]
