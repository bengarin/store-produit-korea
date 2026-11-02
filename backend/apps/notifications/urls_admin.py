from django.urls import path

from . import views

urlpatterns = [
    path("notifications/emails", views.EmailStatusView.as_view(), name="admin-emails"),
    path("notifications/emails/test", views.EmailTestView.as_view(), name="admin-emails-test"),
]
