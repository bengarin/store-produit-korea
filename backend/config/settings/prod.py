"""Production : tout réglage sensible est obligatoire et vient de l'environnement."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import env

DEBUG = False

SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="")
if len(SECRET_KEY) < 40:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY manquante ou trop courte (40 caractères minimum).")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS doit être défini en production.")

# HTTPS obligatoire
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# Préchargement HSTS : engagement difficile à annuler (tous les sous-domaines en HTTPS pour des mois).
# À activer seulement quand le domaine définitif est en HTTPS partout (docs/PRODUCTION.md).
SECURE_HSTS_PRELOAD = env.bool("DJANGO_HSTS_PRELOAD", default=False)
if not SECURE_HSTS_PRELOAD:
    SILENCED_SYSTEM_CHECKS = ["security.W021"]

# Cache PARTAGÉ entre les processus gunicorn (table MySQL) : sans lui, chaque processus a ses propres
# compteurs et les limites anti-abus (connexion, commandes…) sont multipliées par le nombre
# de processus. Créer la table une fois : python manage.py createcachetable
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "mpc_cache",
        "OPTIONS": {"MAX_ENTRIES": 20000},
    }
}
