import pytest
from django.test import override_settings

from apps.accounts.roles import Role
from apps.audit.models import AuditLog
from tests.conftest import PASSWORD, csrf_token, login


@pytest.mark.django_db
def test_connexion_reussie_ouvre_une_session(client, make_user):
    make_user(email="admin@exemple.ma", role=Role.ADMIN)
    response = login(client, "ADMIN@exemple.ma")
    assert response.status_code == 200
    assert response.json()["user"] == {
        "id": response.json()["user"]["id"],
        "email": "admin@exemple.ma",
        "firstName": "",
        "lastName": "",
        "role": "admin",
        "roleLabel": "Administrateur",
    }
    cookie = response.cookies["mpc_session"]
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"
    me = client.get("/api/v1/admin/auth/me")
    assert me.status_code == 200 and me.json()["user"]["role"] == "admin"
    assert AuditLog.objects.filter(action="auth.login", actor__email="admin@exemple.ma").exists()


@pytest.mark.django_db
def test_la_session_change_a_la_connexion(client, make_user):
    make_user(email="a@exemple.ma")
    csrf_token(client)
    client.cookies["mpc_session"] = "valeur-imposee-par-un-attaquant"
    response = login(client, "a@exemple.ma")
    assert response.cookies["mpc_session"].value != "valeur-imposee-par-un-attaquant"


@pytest.mark.django_db
@pytest.mark.parametrize("email,password", [("a@exemple.ma", "mauvais"), ("inconnu@exemple.ma", PASSWORD)])
def test_echec_message_generique(client, make_user, email, password):
    make_user(email="a@exemple.ma")
    response = login(client, email, password)
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "E-mail ou mot de passe incorrect."
    log = AuditLog.objects.get(action="auth.login_failed")
    assert log.changes["email"] == email
    assert PASSWORD not in str(log.changes) and "mauvais" not in str(log.changes)


@pytest.mark.django_db
def test_compte_sans_role_ou_inactif_refuse(client, make_user):
    make_user(email="sans-role@exemple.ma", role=None)
    make_user(email="inactif@exemple.ma", is_active=False)
    for email in ("sans-role@exemple.ma", "inactif@exemple.ma"):
        response = login(client, email)
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "E-mail ou mot de passe incorrect."


@pytest.mark.django_db
@override_settings(AXES_FAILURE_LIMIT=3)
def test_verrouillage_apres_echecs_repetes(client, make_user):
    make_user(email="cible@exemple.ma")
    for _ in range(3):
        login(client, "cible@exemple.ma", "mauvais")
    # Même le BON mot de passe est refusé tant que le verrou est actif.
    response = login(client, "cible@exemple.ma")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "account_locked"
    assert AuditLog.objects.filter(action="auth.login_locked").exists()


@pytest.mark.django_db
def test_deconnexion(client, make_user):
    make_user(email="a@exemple.ma")
    token = login(client, "a@exemple.ma").json()["csrfToken"]
    assert client.post("/api/v1/admin/auth/logout", HTTP_X_CSRFTOKEN=token).status_code == 204
    assert client.get("/api/v1/admin/auth/me").status_code == 403
    assert AuditLog.objects.filter(action="auth.logout").exists()


@pytest.mark.django_db
def test_deconnexion_sans_csrf_refusee(client, make_user):
    make_user(email="a@exemple.ma")
    login(client, "a@exemple.ma")
    response = client.post("/api/v1/admin/auth/logout")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


@pytest.mark.django_db
def test_role_retire_bloque_l_acces_immediatement(client, make_user):
    user = make_user(email="a@exemple.ma")
    login(client, "a@exemple.ma")
    user.set_role(None)
    assert client.get("/api/v1/admin/auth/me").status_code == 403


@pytest.mark.django_db
def test_changement_de_mot_de_passe(client, make_user):
    make_user(email="a@exemple.ma")
    token = login(client, "a@exemple.ma").json()["csrfToken"]
    bad = client.post(
        "/api/v1/admin/auth/password",
        {"currentPassword": "faux", "newPassword": "Nouveau-Mot-De-Passe-99"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert bad.status_code == 400 and "currentPassword" in bad.json()["error"]["fields"]
    weak = client.post(
        "/api/v1/admin/auth/password",
        {"currentPassword": PASSWORD, "newPassword": "123"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert weak.status_code == 400 and "newPassword" in weak.json()["error"]["fields"]
    ok = client.post(
        "/api/v1/admin/auth/password",
        {"currentPassword": PASSWORD, "newPassword": "Nouveau-Mot-De-Passe-99"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert ok.status_code == 204
    assert client.get("/api/v1/admin/auth/me").status_code == 200  # la session courante reste valide
    assert AuditLog.objects.filter(action="auth.password_change").exists()
