from django.urls import path

from . import views

urlpatterns = [
    path("theme", views.ThemeView.as_view(), name="admin-theme"),
    path("theme/draft", views.DraftView.as_view(), name="admin-theme-draft"),
    path("theme/publish", views.PublishView.as_view(), name="admin-theme-publish"),
    path("theme/versions", views.VersionListView.as_view(), name="admin-theme-versions"),
    path("theme/versions/<int:number>", views.VersionDetailView.as_view(), name="admin-theme-version"),
    path("theme/versions/<int:number>/restore", views.RestoreView.as_view(), name="admin-theme-restore"),
    path("theme/versions/<int:number>/load", views.LoadView.as_view(), name="admin-theme-load"),
]
