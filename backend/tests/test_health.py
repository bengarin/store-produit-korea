from unittest import mock

import pytest
from django.db import connection


@pytest.mark.django_db
def test_la_base_de_test_est_bien_mysql():
    assert connection.vendor == "mysql"


@pytest.mark.django_db
def test_health_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "version": "0.1.0"}


@pytest.mark.django_db
def test_health_base_indisponible_renvoie_503_au_format_commun(client):
    with mock.patch("apps.core.views.connection.cursor", side_effect=Exception("down")):
        response = client.get("/api/v1/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "service_unavailable"
    assert "down" not in str(body)  # aucun détail technique exposé
