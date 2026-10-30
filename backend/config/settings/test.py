"""Tests automatisés : MySQL réel (base test_<DB_NAME>), hachage rapide."""

from .base import *  # noqa: F403
from .base import REST_FRAMEWORK

DEBUG = False
SECRET_KEY = "test-only-key"  # noqa: S105 - clé de test, sans valeur réelle
ALLOWED_HOSTS = ["testserver", "localhost"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # accélère les tests uniquement
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        "anon": "1000/min",
        "user": "1000/min",
        "login": "1000/min",
        "orders": "1000/min",
        "promo": "1000/min",
    },
}
