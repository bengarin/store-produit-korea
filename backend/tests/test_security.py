"""Phase 7 — sécurité : IP réelle, routes fermées, configuration de production, connexion et sessions."""

import os
import subprocess
import sys

import pytest
from django.core.management import call_command
from django.test import RequestFactory, override_settings
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.request import Request
from rest_framework.test import APIClient
from rest_framework.throttling import AnonRateThrottle

from apps.accounts.roles import Role
from apps.audit.models import AuditLog
from apps.core.middleware import TrustedProxyMiddleware
from tests.conftest import PASSWORD, csrf_token, login

# --- IP réelle et limites de débit -------------------------------------------------------------


def test_limites_de_debit_insensibles_a_un_x_forwarded_for_forge():
    rf = RequestFactory()
    idents = {
        AnonRateThrottle().get_ident(Request(rf.post("/x", HTTP_X_FORWARDED_FOR=fake, REMOTE_ADDR="9.9.9.9")))
        for fake in ("1.1.1.1", "2.2.2.2", "3.3.3.3, 4.4.4.4")
    }
    assert idents == {"9.9.9.9"}  # avant la phase 7 : 3 identités différentes (contournement)


@pytest.mark.parametrize(
    "count,xff,expected",
    [
        (0, "1.2.3.4", "10.0.0.1"),  # accès direct : en-tête ignoré
        (1, "6.6.6.6, 1.2.3.4", "1.2.3.4"),  # derrière 1 proxy : l'adresse ajoutée par NOTRE proxy
        (1, "", "10.0.0.1"),  # pas d'en-tête : adresse du proxy
        (1, "pas-une-ip", "10.0.0.1"),  # en-tête invalide : jamais pris en compte
        (2, "6.6.6.6, 1.2.3.4, 10.0.0.9", "1.2.3.4"),
    ],
)
def test_ip_reelle_derriere_proxy_de_confiance(count, xff, expected):
    seen = {}
    with override_settings(TRUSTED_PROXY_COUNT=count):
        mw = TrustedProxyMiddleware(lambda r: seen.setdefault("ip", r.META["REMOTE_ADDR"]))
        mw(RequestFactory().get("/", HTTP_X_FORWARDED_FOR=xff, REMOTE_ADDR="10.0.0.1"))
    assert seen["ip"] == expected


# --- Toutes les routes d'administration sont fermées sans session ------------------------------

PUBLIC_ADMIN = {"auth/csrf", "auth/login"}


def admin_routes():
    out = []

    def walk(patterns, prefix):
        for p in patterns:
            if isinstance(p, URLResolver):
                walk(p.url_patterns, prefix + str(p.pattern))
            elif isinstance(p, URLPattern):
                route = prefix + str(p.pattern)
                if route.startswith("api/v1/admin/"):
                    out.append(route.replace("<int:pk>", "1").replace("<int:number>", "1").replace("<int:id>", "1"))

    walk(get_resolver().url_patterns, "")
    return sorted(set(out))


@pytest.mark.django_db
def test_toutes_les_routes_admin_refusent_les_visiteurs():
    client = APIClient()
    routes = admin_routes()
    assert len(routes) >= 50
    for route in routes:
        if route.removeprefix("api/v1/admin/") in PUBLIC_ADMIN:
            continue
        for method in ("get", "post", "put", "patch", "delete"):
            response = getattr(client, method)(f"/{route}", {}, format="json")
            assert response.status_code in (401, 403, 405), (method, route, response.status_code)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "prefix", ["orders", "customers", "analytics/report", "newsletter/subscribers", "inventory/adjust"]
)
def test_editeur_de_contenu_sans_acces_aux_donnees_personnelles(staff, prefix):
    api = staff(Role.CONTENT_EDITOR)
    method = api.post if prefix == "inventory/adjust" else api.get
    assert method(f"/api/v1/admin/{prefix}", {}, format="json").status_code == 403


# --- Configuration de production ----------------------------------------------------------------


def run_prod(code, extra_env=None):
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.prod",
        "DJANGO_ENV_FILE": "none",
        **(extra_env or {}),
    }
    for k in ("DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS", "DJANGO_DEBUG"):
        if not (extra_env and k in extra_env):
            env.pop(k, None)
    return subprocess.run(  # noqa: S603 - code de test fixe, aucune entrée externe
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, cwd=os.getcwd()
    )


def test_production_refuse_de_demarrer_sans_secret_ni_hotes():
    r = run_prod("import django; django.setup()", {"DJANGO_SECRET_KEY": ""})
    assert r.returncode != 0 and "DJANGO_SECRET_KEY" in r.stderr
    r = run_prod("import django; django.setup()", {"DJANGO_SECRET_KEY": "x" * 50})
    assert r.returncode != 0 and "DJANGO_ALLOWED_HOSTS" in r.stderr


def test_production_check_deploy_sans_avertissement():
    env = {
        "DJANGO_SECRET_KEY": "k" * 30 + "Zq8!xP2#vL9@mN4$wR7%" * 2,
        "DJANGO_ALLOWED_HOSTS": "boutique.exemple.ma",
        "DJANGO_DEBUG": "true",
    }
    code = (
        "import django; django.setup(); from django.conf import settings as s; "
        "print(s.DEBUG, s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE, s.SESSION_COOKIE_HTTPONLY, "
        "s.SECURE_SSL_REDIRECT, s.SECURE_HSTS_SECONDS > 0, "
        "s.CACHES['default']['BACKEND'].rsplit('.', 1)[-1])"
    )
    r = run_prod(code, env)
    assert r.returncode == 0, r.stderr
    assert (
        r.stdout.strip() == "False True True True True True DatabaseCache"
    )  # DEBUG forcé à False même si demandé ; cache partagé entre processus (limites anti-abus fiables)
    r = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        env={**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings.prod", **env},
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


# --- Connexion (e-mail + mot de passe, sans double authentification) -------------------------------


def connect(make_user, role=Role.ADMIN, email="equipe@exemple.ma"):
    user = make_user(email=email, role=role)
    client = APIClient(enforce_csrf_checks=True)
    response = login(client, email)
    assert response.status_code == 200, response.content
    client.credentials(HTTP_X_CSRFTOKEN=response.json()["csrfToken"])
    return user, client, response.json()


@pytest.mark.django_db
@pytest.mark.parametrize("role", list(Role))
def test_connexion_sans_code_pour_chaque_role(make_user, role):
    user, client, data = connect(make_user, role=role, email=f"{role.value}@exemple.ma")
    assert set(data) == {"user", "csrfToken"} and data["user"]["role"] == role.value  # aucune étape OTP
    me = client.get("/api/v1/admin/auth/me")
    assert me.status_code == 200 and set(me.json()) == {"user"}
    assert client.get("/api/v1/admin/products").status_code == 200  # page protégée accessible directement
    assert AuditLog.objects.filter(action="auth.login", actor=user).exists()


@pytest.mark.django_db
def test_mauvais_mot_de_passe_et_anonyme_toujours_refuses(make_user):
    make_user(email="equipe@exemple.ma", role=Role.ADMIN)
    assert login(APIClient(), "equipe@exemple.ma", password="mauvais-mot-de-passe").status_code == 401
    assert APIClient().get("/api/v1/admin/products").status_code == 403


def test_plus_aucune_route_de_double_authentification():
    def walk(patterns, prefix=""):
        for p in patterns:
            if isinstance(p, URLResolver):
                yield from walk(p.url_patterns, prefix + str(p.pattern))
            elif isinstance(p, URLPattern):
                yield prefix + str(p.pattern)

    routes = list(walk(get_resolver().url_patterns))
    assert routes and not [r for r in routes if "2fa" in r.lower() or "otp" in r.lower()]


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["verify", "setup", "confirm", "backup-codes", "disable"])
def test_anciennes_routes_2fa_introuvables(make_user, path):
    _, client, _ = connect(make_user)
    assert client.post(f"/api/v1/admin/auth/2fa/{path}", {"code": "123456"}, format="json").status_code == 404


@pytest.mark.django_db
def test_revocation_des_sessions(make_user):
    user, first, _ = connect(make_user)
    second = APIClient(enforce_csrf_checks=True)
    second.credentials(HTTP_X_CSRFTOKEN=login(second, user.email).json()["csrfToken"])
    assert second.get("/api/v1/admin/auth/me").status_code == 200
    assert first.post("/api/v1/admin/auth/sessions/revoke").json() == {"revoked": 1}
    assert second.get("/api/v1/admin/auth/me").status_code == 403  # l'autre appareil est déconnecté
    assert first.get("/api/v1/admin/auth/me").status_code == 200  # la session en cours reste ouverte

    call_command("revoke_sessions", email=user.email, deactivate=True)
    assert first.get("/api/v1/admin/auth/me").status_code == 403  # toutes les sessions fermées
    user.refresh_from_db()
    assert user.is_active is False
    assert login(APIClient(), user.email).status_code == 401
    assert AuditLog.objects.filter(action="auth.sessions_revoked_by_server").count() == 1


@pytest.mark.django_db
def test_changement_de_mot_de_passe_ferme_les_autres_sessions(make_user):
    user, first, _ = connect(make_user)
    second = APIClient(enforce_csrf_checks=True)
    second.credentials(HTTP_X_CSRFTOKEN=login(second, user.email).json()["csrfToken"])
    new = "Un-Nouveau-Mot-De-Passe-2026"
    r = first.post("/api/v1/admin/auth/password", {"currentPassword": PASSWORD, "newPassword": new}, format="json")
    assert r.status_code == 204
    assert second.get("/api/v1/admin/auth/me").status_code == 403
    assert first.get("/api/v1/admin/auth/me").status_code == 200
    csrf_token(APIClient())
