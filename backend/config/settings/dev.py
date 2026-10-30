"""Développement local (DEBUG, clé de dev si aucune n'est fournie)."""

from .base import *  # noqa: F403
from .base import env

DEBUG = env.bool("DJANGO_DEBUG", default=True)
# Clé UNIQUEMENT pour le développement local : jamais utilisée en production (prod.py l'exige).
SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="") or "dev-only-insecure-key-do-not-use-in-production"
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
