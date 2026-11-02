"""Visuels marketing : séparés des photos du produit, gérés dans l'admin, publiés selon des règles strictes."""

import pytest

from apps.accounts.roles import Role
from apps.catalog.models import ProductImage, ProductMarketingImage

P = "/api/v1/admin/products"


@pytest.fixture
def setup(staff, sellable, media):
    p = sellable(slug="gel-mkt", stock=5)
    return p, staff(Role.CONTENT_EDITOR), media


def add(api, product, media, **data):
    body = {"mediaId": media(color=(data.pop("c", 50), 60, 70)).pk, **data}
    return api.post(f"{P}/{product.pk}/marketing-images", body, format="json")


@pytest.mark.django_db
def test_ajout_ordre_et_publication(client, setup):
    p, api, media = setup
    gallery_before = list(ProductImage.objects.filter(product=p).values_list("pk", "media_id"))
    a = add(api, p, media, category="banner", language="fr", title="Présentation", c=1).json()
    b = add(api, p, media, category="usage", language="any", c=2).json()
    c = add(api, p, media, category="benefits", language="ar", description="وصف", c=3).json()
    assert [a["position"], b["position"], c["position"]] == [0, 1, 2]
    assert (
        list(ProductImage.objects.filter(product=p).values_list("pk", "media_id")) == gallery_before
    )  # galerie intacte

    assert (
        api.post(
            f"{P}/{p.pk}/marketing-images/reorder", {"ids": [c["id"], a["id"], b["id"]]}, format="json"
        ).status_code
        == 204
    )
    item = client.get(f"/api/v1/store/products/{p.slug}").json()
    assert [m["id"] for m in item["marketing"]] == [c["id"], a["id"], b["id"]]
    first = item["marketing"][0]
    assert first["category"] == "benefits" and first["language"] == "ar" and first["description"] == "وصف"
    assert first["src"].endswith(".webp") and first["width"] > 0
    assert all(g["src"] != m["src"] for g in item["galleryImages"] for m in item["marketing"])  # jamais mélangés


@pytest.mark.django_db
def test_desactive_et_remplacement(client, setup):
    p, api, media = setup
    a = add(api, p, media, category="banner", c=4).json()
    assert api.patch(f"/api/v1/admin/marketing-images/{a['id']}", {"isActive": False}, format="json").status_code == 200
    assert "marketing" not in client.get(f"/api/v1/store/products/{p.slug}").json()  # aucune section vide
    new_media = media(color=(9, 9, 9))
    r = api.patch(
        f"/api/v1/admin/marketing-images/{a['id']}", {"mediaId": new_media.pk, "isActive": True}, format="json"
    )
    assert r.status_code == 200 and r.json()["mediaId"] == new_media.pk
    assert client.get(f"/api/v1/store/products/{p.slug}").json()["marketing"][0]["src"] == new_media.url


@pytest.mark.django_db
def test_avant_apres_jamais_publie_sans_confirmation(client, setup):
    p, api, media = setup
    r = add(api, p, media, category="before_after", c=5)
    assert r.status_code == 400 and "authenticConfirmed" in r.json()["error"]["fields"]
    hidden = add(api, p, media, category="before_after", isActive=False, c=6).json()  # enregistré mais masqué
    assert "marketing" not in client.get(f"/api/v1/store/products/{p.slug}").json()
    r = api.patch(f"/api/v1/admin/marketing-images/{hidden['id']}", {"isActive": True}, format="json")
    assert r.status_code == 400
    r = api.patch(
        f"/api/v1/admin/marketing-images/{hidden['id']}", {"isActive": True, "authenticConfirmed": True}, format="json"
    )
    assert r.status_code == 200 and r.json()["isPublic"] is True
    # Confirmation forcée en base mais retirée ensuite : redevient invisible
    ProductMarketingImage.objects.filter(pk=hidden["id"]).update(authentic_confirmed=False)
    assert "marketing" not in client.get(f"/api/v1/store/products/{p.slug}").json()


@pytest.mark.django_db
def test_chaque_produit_ses_visuels_et_reordre_protege(staff, sellable, media):
    api = staff(Role.ADMIN)
    p1, p2 = sellable(slug="p-un", stock=5), sellable(slug="p-deux", stock=5)
    a = add(api, p1, media, category="banner", c=7).json()
    b = add(api, p2, media, category="banner", c=8).json()
    r = api.post(f"{P}/{p1.pk}/marketing-images/reorder", {"ids": [a["id"], b["id"]]}, format="json")
    assert r.status_code == 400  # visuel d'un autre produit refusé
    assert [m["id"] for m in api.get(f"{P}/{p1.pk}/marketing-images").json()["items"]] == [a["id"]]


@pytest.mark.django_db
@pytest.mark.parametrize("role,code", [(Role.ORDER_MANAGER, 403), (Role.ANALYST, 403), (None, 403)])
def test_seules_les_equipes_catalogue_ecrivent(staff, sellable, media, role, code):
    p = sellable(slug="gel-mkt", stock=5)
    assert add(staff(role), p, media, category="banner", c=9).status_code == code
    assert not ProductMarketingImage.objects.exists()


@pytest.mark.django_db
def test_suppression_garde_le_media_et_media_utilise_protege(setup, staff):
    p, api, media = setup
    admin_api = staff(Role.ADMIN)  # seuls Propriétaire/Admin suppriment des médias
    a = add(api, p, media, category="banner", c=10).json()
    r = admin_api.delete(f"/api/v1/admin/media/{a['mediaId']}")
    assert r.status_code == 409  # utilisé par un visuel marketing : non supprimable
    assert api.delete(f"/api/v1/admin/marketing-images/{a['id']}").status_code == 403  # éditeur : pas de suppression
    assert admin_api.delete(f"/api/v1/admin/marketing-images/{a['id']}").status_code == 204
    assert not ProductMarketingImage.objects.exists()
    assert admin_api.delete(f"/api/v1/admin/media/{a['mediaId']}").status_code == 204  # libre ensuite
