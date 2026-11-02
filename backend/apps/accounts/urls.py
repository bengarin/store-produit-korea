from django.urls import path

from . import views, views_2fa

urlpatterns = [
    path("csrf", views.CsrfView.as_view(), name="auth-csrf"),
    path("login", views.LoginView.as_view(), name="auth-login"),
    path("logout", views.LogoutView.as_view(), name="auth-logout"),
    path("me", views.MeView.as_view(), name="auth-me"),
    path("password", views.PasswordChangeView.as_view(), name="auth-password"),
    path("2fa/verify", views_2fa.VerifyView.as_view(), name="auth-2fa-verify"),
    path("2fa/setup", views_2fa.SetupView.as_view(), name="auth-2fa-setup"),
    path("2fa/confirm", views_2fa.ConfirmView.as_view(), name="auth-2fa-confirm"),
    path("2fa/backup-codes", views_2fa.BackupCodesView.as_view(), name="auth-2fa-backup"),
    path("2fa/disable", views_2fa.DisableView.as_view(), name="auth-2fa-disable"),
    path("sessions/revoke", views_2fa.RevokeSessionsView.as_view(), name="auth-sessions-revoke"),
]
