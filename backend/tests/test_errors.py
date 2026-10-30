import pytest
from django.test import override_settings

from tests.conftest import csrf_token


def assert_error(response, status, code):
    assert response.status_code == status
    assert response["Content-Type"].startswith("application/json")
    body = response.json()
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    return body["error"]


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_route_inconnue_renvoie_404_json(client):
    assert_error(client.get("/api/v1/nexiste-pas"), 404, "not_found")


@pytest.mark.django_db
def test_methode_non_autorisee(client):
    assert_error(client.post("/api/v1/health"), 405, "method_not_allowed")


@pytest.mark.django_db
def test_route_protegee_sans_session(client):
    assert_error(client.get("/api/v1/admin/auth/me"), 403, "not_authenticated")


@pytest.mark.django_db
def test_erreur_de_validation_detaille_les_champs(client):
    token = csrf_token(client)
    response = client.post("/api/v1/admin/auth/login", {"email": "pas-un-email"}, format="json", HTTP_X_CSRFTOKEN=token)
    error = assert_error(response, 400, "validation_error")
    assert set(error["fields"]) == {"email", "password"}


@pytest.mark.django_db
def test_json_mal_forme(client):
    token = csrf_token(client)
    response = client.post(
        "/api/v1/admin/auth/login", "{pas du json", content_type="application/json", HTTP_X_CSRFTOKEN=token
    )
    assert_error(response, 400, "parse_error")


@pytest.mark.django_db
def test_csrf_manquant(client):
    response = client.post("/api/v1/admin/auth/login", {"email": "a@b.ma", "password": "x"}, format="json")
    assert_error(response, 403, "csrf_failed")
