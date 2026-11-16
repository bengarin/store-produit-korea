from django.urls import path

from . import views

urlpatterns = [
    path("blog/articles", views.ArticleListCreateView.as_view(), name="admin-blog-articles"),
    path("blog/articles/<int:pk>", views.ArticleDetailView.as_view(), name="admin-blog-article"),
]
