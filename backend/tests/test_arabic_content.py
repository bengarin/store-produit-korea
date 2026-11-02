"""Contenus arabes des produits et catégories : saisis dans l'admin, indépendants du français, publiés tels quels."""

import pytest

from apps.accounts.roles import Role
from apps.catalog.models import Category, Product

P = "/api/v1/admin/products"
AR = {
    "displayNameAr": "جل الصبار المهدّئ",
    "cardLineAr": "جل منعش وخفيف.",
    "summaryAr": "جل بالألوفيرا لترطيب البشرة.",
    "descriptionHtmlAr": "<p>نص <strong>مهم</strong></p><script>alert(1)</script>",
    "ingredientsAr": ["ألوفيرا"],
    "benefitsAr": ["انتعاش"],
    "usageAr": ["يُوضع على بشرة نظيفة."],
    "skinTypesAr": "جميع أنواع البشرة",
}


@pytest.mark.django_db
def test_admin_enregistre_l_arabe_sans_toucher_au_francais(staff, sellable):
    p = sellable(slug="gel-ar", stock=5)
    before = Product.objects.values("display_name", "summary", "short_description", "ingredients").get(pk=p.pk)
    api = staff(Role.CONTENT_EDITOR)
    r = api.patch(f"{P}/{p.pk}", AR, format="json")
    assert r.status_code == 200, r.content
    body = r.json()
    assert body["displayNameAr"] == AR["displayNameAr"] and body["ingredientsAr"] == ["ألوفيرا"]
    assert "<script" not in body["descriptionHtmlAr"] and "<strong>مهم</strong>" in body["descriptionHtmlAr"]  # assaini
    after = Product.objects.values("display_name", "summary", "short_description", "ingredients").get(pk=p.pk)
    assert after == before  # le français n'a pas bougé


@pytest.mark.django_db
def test_api_publique_expose_seulement_les_champs_arabes_remplis(client, staff, sellable):
    p = sellable(slug="gel-ar", stock=5)
    item = client.get(f"/api/v1/store/products/{p.slug}").json()
    assert "translations" not in item  # rien de saisi : le français sera affiché
    api = staff(Role.ADMIN)
    api.patch(f"{P}/{p.pk}", {"displayNameAr": "اسم", "summaryAr": ""}, format="json")
    api.patch(
        f"{P}/{p.pk}",
        {"highlights": [{"icon": "leaf", "label": "Naturel", "labelAr": "طبيعي"}, {"icon": "sun", "label": "Éclat"}]},
        format="json",
    )
    item = client.get(f"/api/v1/store/products/{p.slug}").json()
    assert item["translations"]["ar"] == {"displayName": "اسم", "highlights": ["طبيعي", None]}
    assert item["displayName"] != "اسم" and item["highlights"][0]["label"] == "Naturel"


@pytest.mark.django_db
def test_categorie_en_arabe(client, staff, category):
    c = category(slug="eclat", name="Éclat")
    assert "translations" not in client.get("/api/v1/store/categories").json()["items"][0]
    r = staff(Role.ADMIN).patch(f"/api/v1/admin/categories/{c.pk}", {"nameAr": "الإشراق"}, format="json")
    assert r.status_code == 200 and r.json()["nameAr"] == "الإشراق"
    assert Category.objects.get(pk=c.pk).name == "Éclat"
    item = client.get("/api/v1/store/categories").json()["items"][0]
    assert item["label"] == "Éclat" and item["translations"] == {"ar": {"label": "الإشراق"}}


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.ORDER_MANAGER, Role.ANALYST])
def test_roles_en_lecture_seule_ne_peuvent_pas_ecrire_l_arabe(staff, sellable, role):
    p = sellable(slug="gel-ar", stock=5)
    assert staff(role).patch(f"{P}/{p.pk}", {"displayNameAr": "اسم"}, format="json").status_code == 403
    assert Product.objects.get(pk=p.pk).display_name_ar == ""


@pytest.mark.django_db
def test_validation_des_champs_arabes(staff, sellable):
    p = sellable(slug="gel-ar", stock=5)
    api = staff(Role.ADMIN)
    r = api.patch(f"{P}/{p.pk}", {"cardLineAr": "ب" * 161, "ingredientsAr": [""]}, format="json")
    assert r.status_code == 400
    assert set(r.json()["error"]["fields"]) >= {"cardLineAr", "ingredientsAr"}


@pytest.mark.django_db
def test_config_publique_identite_legale_vide_puis_saisie(client, staff, shop):
    legal = client.get("/api/v1/store/config").json()["legal"]
    assert legal == {"name": "", "address": "", "email": "", "phone": ""}  # rien d'inventé
    staff(Role.OWNER).patch(
        "/api/v1/admin/settings", {"legalName": "Exemple SARL", "contactEmail": "contact@exemple.ma"}, format="json"
    )
    legal = client.get("/api/v1/store/config").json()["legal"]
    assert legal["name"] == "Exemple SARL" and legal["email"] == "contact@exemple.ma"
