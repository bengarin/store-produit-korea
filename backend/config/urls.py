from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/admin/auth/", include("apps.accounts.urls")),
]

# Réponses JSON (format d'erreur commun) pour les URL inconnues et les erreurs serveur.
handler404 = "apps.core.exceptions.json_404"
handler500 = "apps.core.exceptions.json_500"
