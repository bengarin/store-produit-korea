from django.urls import path

from . import views

urlpatterns = [
    path("newsletter/subscribers", views.SubscriberListView.as_view(), name="admin-newsletter"),
    path("newsletter/export", views.SubscriberExportView.as_view(), name="admin-newsletter-export"),
]
