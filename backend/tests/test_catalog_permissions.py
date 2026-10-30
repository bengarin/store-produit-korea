"""Matrice des 5 rôles (+ sans rôle) sur toutes les familles d'actions du catalogue."""

import pytest

from apps.accounts.roles import Role
from tests.conftest import upload

OWN, A, M, E, N = Role.OWNER, Role.ADMIN, Role.ORDER_MANAGER, Role.CONTENT_EDITOR, Role.ANALYST
READ = {OWN, A, M, E, N}
WRITE = {OWN, A, E}
DELETE = {OWN, A}


def expected(role, allowed, ok):
    return ok if role in allowed else 403


@pytest.mark.django_db
@pytest.mark.parametrize("role", [*Role, None])
def test_lecture(staff, product, role):
    p = product()
    api = staff(role)
    for url in (
        "/api/v1/admin/products",
        f"/api/v1/admin/products/{p.pk}",
        "/api/v1/admin/categories",
        "/api/v1/admin/media",
        f"/api/v1/admin/products/{p.pk}/variants",
        f"/api/v1/admin/products/{p.pk}/images",
    ):
        assert api.get(url).status_code == expected(role, READ, 200), url


@pytest.mark.django_db
@pytest.mark.parametrize("role", [*Role, None])
def test_creation_et_modification(staff, product, role):
    p = product()
    variant = p.variants.get()
    api = staff(role)
    checks = [
        (api.post("/api/v1/admin/products", {"brand": "B", "name": f"N {role}"}, format="json"), 201),
        (api.patch(f"/api/v1/admin/products/{p.pk}", {"cardLine": "x"}, format="json"), 200),
        (api.post(f"/api/v1/admin/products/{p.pk}/status", {"status": "active"}, format="json"), 200),
        (api.patch(f"/api/v1/admin/variants/{variant.pk}", {"lowStockThreshold": 3}, format="json"), 200),
        (api.post("/api/v1/admin/categories", {"name": f"Cat {role}"}, format="json"), 201),
        (api.post("/api/v1/admin/media", {"file": upload()}, format="multipart"), 201),
    ]
    for response, ok in checks:
        assert response.status_code == expected(role, WRITE, ok), response.content


@pytest.mark.django_db
@pytest.mark.parametrize("role", [*Role, None])
def test_suppression(staff, product, category, role):
    p = product(slug="a-supprimer")
    empty = category(slug="vide", name="Vide")
    api = staff(role)
    assert api.delete(f"/api/v1/admin/products/{p.pk}").status_code == expected(role, DELETE, 204)
    assert api.delete(f"/api/v1/admin/categories/{empty.pk}").status_code == expected(role, DELETE, 204)


@pytest.mark.django_db
def test_anonyme_refuse_partout(client, product):
    p = product()
    for method, url in (
        ("get", "/api/v1/admin/products"),
        ("get", f"/api/v1/admin/products/{p.pk}"),
        ("post", "/api/v1/admin/products"),
        ("get", "/api/v1/admin/media"),
    ):
        assert getattr(client, method)(url).status_code == 403


@pytest.mark.django_db
def test_ecriture_admin_sans_csrf_refusee(client, make_user):
    from tests.conftest import login

    make_user(email="admin@exemple.ma", role=Role.ADMIN)
    login(client, "admin@exemple.ma")  # vraie session, client qui applique le CSRF
    response = client.post("/api/v1/admin/products", {"brand": "B", "name": "N"}, format="json")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


@pytest.mark.django_db
@pytest.mark.parametrize("role,sees_cost", [(OWN, True), (A, True), (N, True), (M, False), (E, False)])
def test_cout_visible_selon_le_role(staff, product, role, sees_cost):
    p = product()
    api = staff(role)
    detail = api.get(f"/api/v1/admin/products/{p.pk}").json()
    variants = api.get(f"/api/v1/admin/products/{p.pk}/variants").json()["items"]
    assert ("cost" in detail["variants"][0]) is sees_cost
    assert ("cost" in variants[0]) is sees_cost


@pytest.mark.django_db
def test_editeur_ne_peut_pas_modifier_le_cout(staff, product):
    variant = product().variants.get()
    response = staff(E).patch(f"/api/v1/admin/variants/{variant.pk}", {"cost": "10.00"}, format="json")
    assert response.status_code == 400
    assert "cost" in response.json()["error"]["fields"]
    ok = staff(OWN).patch(f"/api/v1/admin/variants/{variant.pk}", {"cost": "10.00"}, format="json")
    assert ok.status_code == 200 and ok.json()["cost"] == 10.0
