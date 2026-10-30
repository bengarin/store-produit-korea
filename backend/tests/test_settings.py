"""La configuration de production refuse de démarrer sans réglages sûrs."""

import importlib
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured


def load_prod(monkeypatch, **env):
    for key in ("DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    for name in ("config.settings.prod", "config.settings.base"):
        sys.modules.pop(name, None)
    return importlib.import_module("config.settings.prod")


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch):
    # N'utilise pas backend/.env local : le test doit être reproductible.
    monkeypatch.setattr("environ.Env.read_env", lambda *a, **k: None)
    yield
    for name in ("config.settings.prod", "config.settings.base"):
        sys.modules.pop(name, None)


def test_prod_sans_cle_secrete(monkeypatch):
    with pytest.raises(ImproperlyConfigured):
        load_prod(monkeypatch, DJANGO_ALLOWED_HOSTS="mapetitecoree.ma")


def test_prod_sans_hotes_autorises(monkeypatch):
    with pytest.raises(ImproperlyConfigured):
        load_prod(monkeypatch, DJANGO_SECRET_KEY="x" * 50)


def test_prod_securisee(monkeypatch):
    prod = load_prod(monkeypatch, DJANGO_SECRET_KEY="x" * 50, DJANGO_ALLOWED_HOSTS="mapetitecoree.ma")
    assert prod.DEBUG is False
    assert prod.SESSION_COOKIE_SECURE and prod.CSRF_COOKIE_SECURE and prod.SECURE_SSL_REDIRECT
    assert prod.SECURE_HSTS_SECONDS > 0
    assert prod.DATABASES["default"]["ENGINE"] == "django.db.backends.mysql"
