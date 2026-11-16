from django.urls import path

from . import views

urlpatterns = [
    path("blog", views.PublicArticleListView.as_view(), name="store-blog"),
    path("blog/<slug:slug>", views.PublicArticleDetailView.as_view(), name="store-blog-article"),
]
