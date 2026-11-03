"""Le nombre de requêtes SQL des listes ne doit pas grandir avec le nombre de produits (pas de « N+1 »)."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.accounts.roles import Role


def count(client, url):
    with CaptureQueriesContext(connection) as q:
        assert client.get(url).status_code == 200
    return len(q)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url,role",
    [
        ("/api/v1/admin/inventory", Role.ORDER_MANAGER),
        ("/api/v1/admin/products", Role.CONTENT_EDITOR),
        ("/api/v1/store/products", None),
    ],
)
def test_requetes_constantes(staff, sellable, url, role):
    api = staff(role) if role else None
    from rest_framework.test import APIClient

    client = api or APIClient()
    for i in range(2):
        sellable(slug=f"prod-a{i}", stock=5)
    few = count(client, url)
    for i in range(6):
        sellable(slug=f"prod-b{i}", stock=5)
    assert count(client, url) == few  # 2 ou 8 produits : même nombre de requêtes
