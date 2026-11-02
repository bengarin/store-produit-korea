from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/admin/auth/", include("apps.accounts.urls")),
    path("api/v1/admin/", include("apps.catalog.urls_admin")),
    path("api/v1/admin/", include("apps.orders.urls_admin")),
    path("api/v1/admin/", include("apps.themes.urls_admin")),
    path("api/v1/admin/", include("apps.newsletter.urls_admin")),
    path("api/v1/admin/", include("apps.notifications.urls_admin")),
    # Boutique publique : chemins attendus par src/api/endpoints.js
    path("api/v1/store/", include("apps.catalog.urls_public")),
    path("api/v1/store/", include("apps.orders.urls_public")),
    path("api/v1/store/", include("apps.themes.urls_public")),
    path("api/v1/store/", include("apps.newsletter.urls_public")),
]

if settings.DEBUG:  # en développement uniquement ; en production les médias sont servis par le stockage
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Vérification locale du front construit servi par Django (en production : par nginx / le serveur web).
    urlpatterns += [
        re_path(r"^assets/(?P<path>.*)$", serve, {"document_root": settings.FRONTEND_DIST_DIR / "assets"}),
        re_path(
            r"^(?P<path>(favicon-\d+|apple-touch-icon)\.png)$", serve, {"document_root": settings.FRONTEND_DIST_DIR}
        ),
    ]

# Pages HTML de la boutique (titres, descriptions, données structurées) : TOUJOURS en dernier.
urlpatterns += [path("", include("apps.seo.urls"))]

# Réponses JSON (format d'erreur commun) pour les URL inconnues et les erreurs serveur.
handler404 = "apps.core.exceptions.json_404"
handler500 = "apps.core.exceptions.json_500"
