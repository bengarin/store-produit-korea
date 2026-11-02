from django.urls import path

from . import views

urlpatterns = [path("newsletter", views.SubscribeView.as_view(), name="store-newsletter")]
