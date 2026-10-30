import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.roles import Role

PASSWORD = "Un-Mot-De-Passe-Solide-2026"


@pytest.fixture
def client():
    """Client API qui vérifie le CSRF comme un vrai navigateur."""
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def make_user(db):
    def _make(email="equipe@exemple.ma", role: Role | None = Role.ADMIN, **extra):
        user = User.objects.create_user(email=email, password=PASSWORD, **extra)
        if role is not None:
            user.set_role(role)
        return user

    return _make


def csrf_token(client):
    response = client.get("/api/v1/admin/auth/csrf")
    assert response.status_code == 200
    return response.json()["csrfToken"]


def login(client, email, password=PASSWORD):
    token = csrf_token(client)
    return client.post(
        "/api/v1/admin/auth/login", {"email": email, "password": password}, format="json", HTTP_X_CSRFTOKEN=token
    )
