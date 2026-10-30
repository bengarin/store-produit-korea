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


# --- Outils catalogue (phase 1) ---------------------------------------------
import io  # noqa: E402

from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from PIL import Image  # noqa: E402

ALL_ROLES = list(Role)


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    """Chaque test écrit ses fichiers dans un dossier temporaire (jamais dans backend/media)."""
    settings.MEDIA_ROOT = tmp_path / "media"


def image_bytes(fmt="PNG", size=(800, 600), color=(200, 120, 80), **save_kwargs):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt, **save_kwargs)
    return buffer.getvalue()


def upload(name="photo.png", data=None, content_type="image/png"):
    return SimpleUploadedFile(name, data if data is not None else image_bytes(), content_type=content_type)


@pytest.fixture
def staff(make_user):
    """staff(Role.ADMIN) → client API connecté avec ce rôle (CSRF déjà testé en phase 0)."""

    def _staff(role=Role.ADMIN):
        user = make_user(email=f"{role.value if role else 'none'}@exemple.ma", role=role)
        api = APIClient()
        api.force_login(user)
        api.user = user
        return api

    return _staff


@pytest.fixture
def media(db):
    from apps.media_library.services import create_from_upload

    def _media(color=(10, 20, 30)):
        return create_from_upload(upload(data=image_bytes(color=color)))[0]

    return _media


@pytest.fixture
def category(db):
    from apps.catalog.models import Category

    def _category(slug="hydratation", name="Hydratation", **extra):
        return Category.objects.create(slug=slug, name=name, **extra)

    return _category


@pytest.fixture
def product(db, category, media):
    """Produit COMPLET (activable) : catégorie, image, prix. Statut brouillon par défaut."""
    from decimal import Decimal

    from apps.catalog.models import Product, ProductCategory, ProductImage, Variant

    def _product(slug="creme-test", status="draft", price="129.00", **extra):
        p = Product.objects.create(
            slug=slug, brand="Marque", name="Crème test", summary="Une crème.", status=status, **extra
        )
        cat = category(slug=f"cat-{slug}", name=f"Cat {slug}")
        ProductCategory.objects.create(product=p, category=cat)
        ProductImage.objects.create(product=p, media=media(color=(len(slug) * 7 % 255, 1, 2)), alt="Photo")
        Variant.objects.create(
            product=p,
            price=Decimal(price),
            is_default=True,
            title="Par défaut",
            cost=Decimal("40.00"),
            stock_quantity=10,
        )
        return p

    return _product
