from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/admin/auth/", include("apps.accounts.urls")),
    path("api/v1/admin/", include("apps.catalog.urls_admin")),
    # Boutique publique : chemins attendus par src/api/endpoints.js
    path("api/v1/store/", include("apps.catalog.urls_public")),
]

if settings.DEBUG:  # en développement uniquement ; en production les médias sont servis par le stockage
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Réponses JSON (format d'erreur commun) pour les URL inconnues et les erreurs serveur.
handler404 = "apps.core.exceptions.json_404"
handler500 = "apps.core.exceptions.json_500"
