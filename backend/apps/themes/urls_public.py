from django.urls import path

from . import views

urlpatterns = [path("theme", views.PublicThemeView.as_view(), name="store-theme")]
