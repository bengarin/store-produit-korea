from decimal import Decimal
from unittest import mock

import pytest

from apps.audit.models import AuditLog
from apps.catalog.models import Product, ProductImage, Variant

P = "/api/v1/admin/products"


@pytest.fixture
def api(staff):
    return staff()  # Administrateur


# --- Création / lecture / modification ------------------------------------
@pytest.mark.django_db
def test_creer_un_produit_brouillon(api, category):
    hyd, eclat = category(), category(slug="eclat", name="Éclat")
    response = api.post(
        P,
        {
            "brand": "Marque",
            "name": "Sérum Éclat",
            "cardLine": "Un sérum.",
            "summary": "Description.",
            "categoryIds": [eclat.pk, hyd.pk],
            "ingredients": ["Eau", "Niacinamide"],
            "usage": ["Appliquer."],
            "highlights": [{"icon": "leaf", "label": "Vegan"}],
            "variant": {"price": "149.00", "sku": "SER-01", "stockQuantity": 12},
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    data = response.json()
    assert data["slug"] == "marque-serum-eclat" and data["status"] == "draft"
    assert [c["slug"] for c in data["categories"]] == ["eclat", "hydratation"]  # ordre conservé
    assert data["variants"][0] | {} and data["variants"][0]["price"] == 149.0
    assert data["variants"][0]["isDefault"] and data["variants"][0]["sku"] == "SER-01"
    assert "Au moins une image dans la galerie est obligatoire." in data["activationErrors"]
    assert AuditLog.objects.filter(action="product.create", target_id=str(data["id"])).exists()


@pytest.mark.django_db
def test_validation_des_champs(api):
    response = api.post(
        P, {"brand": "", "highlights": [{"icon": "fusee", "label": "x"}], "variant": {"price": "-3"}}, format="json"
    )
    fields = response.json()["error"]["fields"]
    assert response.status_code == 400
    assert {"brand", "name", "highlights", "variant"} <= set(fields)


@pytest.mark.django_db
def test_slug_unique_et_genere(api, product):
    product(slug="marque-creme")
    response = api.post(P, {"brand": "Marque", "name": "Crème"}, format="json")
    assert response.json()["slug"] == "marque-creme-2"
    dup = api.post(P, {"brand": "X", "name": "Y", "slug": "marque-creme"}, format="json")
    assert dup.status_code == 400 and "slug" in dup.json()["error"]["fields"]


@pytest.mark.django_db
def test_description_html_assainie(api, product):
    p = product()
    html = '<p onclick="x()">Bonjour <script>alert(1)</script><a href="javascript:alert(1)">lien</a></p>'
    data = api.patch(f"{P}/{p.pk}", {"descriptionHtml": html}, format="json").json()
    assert "script" not in data["descriptionHtml"] and "onclick" not in data["descriptionHtml"]
    assert "javascript:" not in data["descriptionHtml"] and "Bonjour" in data["descriptionHtml"]


@pytest.mark.django_db
def test_modification_tracee_dans_l_audit(api, product):
    p = product()
    api.patch(f"{P}/{p.pk}", {"brand": "Nouvelle", "seoTitle": "Titre SEO"}, format="json")
    log = AuditLog.objects.get(action="product.update")
    assert log.changes["brand"] == ["Marque", "Nouvelle"]
    assert log.actor.email == "admin@exemple.ma"


@pytest.mark.django_db
def test_liste_filtres_recherche_pagination(api, product):
    product(slug="aloe", status="active")
    product(slug="yuja", status="draft")
    assert [p["slug"] for p in api.get(f"{P}?status=active").json()["items"]] == ["aloe"]
    assert [p["slug"] for p in api.get(f"{P}?search=yuja").json()["items"]] == ["yuja"]
    page = api.get(f"{P}?page_size=1").json()
    assert page["total"] == 2 and page["pageSize"] == 1 and len(page["items"]) == 1
    assert api.get(f"{P}?category=cat-aloe").json()["items"][0]["slug"] == "aloe"


# --- Statuts et conditions d'activation ------------------------------------
@pytest.mark.django_db
def test_activation_refusee_si_incomplet(api):
    p = api.post(P, {"brand": "B", "name": "Incomplet"}, format="json").json()
    response = api.post(f"{P}/{p['id']}/status", {"status": "active"}, format="json")
    assert response.status_code == 400
    errors = response.json()["error"]["fields"]["status"]
    assert "Au moins une catégorie est obligatoire." in errors
    assert "Le prix doit être supérieur à 0." in errors
    assert Product.objects.get(pk=p["id"]).status == "draft"


@pytest.mark.django_db
def test_activation_puis_archivage(api, product):
    p = product()
    active = api.post(f"{P}/{p.pk}/status", {"status": "active"}, format="json").json()
    assert active["status"] == "active" and active["publishedAt"]
    assert api.post(f"{P}/{p.pk}/status", {"status": "archived"}, format="json").json()["status"] == "archived"
    assert AuditLog.objects.filter(action="product.status").count() == 2


@pytest.mark.django_db
def test_produit_actif_ne_peut_pas_devenir_incomplet(api, product):
    p = product(status="active")
    image = p.images.get()
    assert api.delete(f"/api/v1/admin/product-images/{image.pk}").status_code == 400
    assert ProductImage.objects.filter(pk=image.pk).exists()  # annulé (transaction)
    assert api.patch(f"{P}/{p.pk}", {"categoryIds": []}, format="json").status_code == 400
    assert p.category_links.count() == 1
    variant = p.variants.get()
    assert api.patch(f"/api/v1/admin/variants/{variant.pk}", {"price": "0"}, format="json").status_code == 400
    assert Variant.objects.get(pk=variant.pk).price == Decimal("129.00")


# --- Suppression ---------------------------------------------------------
@pytest.mark.django_db
def test_suppression_selon_statut(api, product):
    active, draft = product(slug="actif", status="active"), product(slug="brouillon")
    response = api.delete(f"{P}/{active.pk}")
    assert response.status_code == 409 and response.json()["error"]["code"] == "product_active"
    assert api.delete(f"{P}/{draft.pk}").status_code == 204
    assert AuditLog.objects.filter(action="product.delete").exists()


@pytest.mark.django_db
def test_produit_deja_commande_jamais_supprime(api, product):
    p = product(status="archived")
    # Simule une ligne de commande (la table des commandes arrive en phase 2).
    with mock.patch("apps.catalog.services.external_references", return_value=1):
        response = api.delete(f"{P}/{p.pk}")
    assert response.status_code == 409 and response.json()["error"]["code"] == "product_in_use"
    assert Product.objects.filter(pk=p.pk).exists()


def test_detection_generique_des_references_externes():
    """Toute table hors catalogue qui pointe vers un produit/une variante bloquera la suppression."""
    from apps.catalog.services import external_references

    fake_rel = mock.Mock(one_to_many=True, one_to_one=False)
    fake_rel.related_model._meta.app_label = "orders"
    fake_rel.related_model._base_manager.filter.return_value.count.return_value = 2
    fake_rel.field.name = "variant"
    instance = mock.Mock()
    instance._meta.related_objects = [fake_rel]
    assert external_references(instance) == 2


# --- Options et variantes ----------------------------------------------
@pytest.mark.django_db
def test_options_et_variantes(api, product):
    p = product()
    default = p.variants.get()
    opts = api.put(f"{P}/{p.pk}/options", [{"name": "Contenance", "values": ["50 ml", "100 ml"]}], format="json")
    assert opts.status_code == 200 and opts.json()[0]["values"] == ["50 ml", "100 ml"]

    upd = api.patch(f"/api/v1/admin/variants/{default.pk}", {"optionValues": {"Contenance": "50 ml"}}, format="json")
    assert upd.status_code == 200 and upd.json()["title"] == "50 ml"
    big = api.post(
        f"{P}/{p.pk}/variants",
        {"price": "199.00", "optionValues": {"Contenance": "100 ml"}, "stockQuantity": 4},
        format="json",
    )
    assert big.status_code == 201 and big.json()["title"] == "100 ml" and not big.json()["isDefault"]

    dup = api.post(f"{P}/{p.pk}/variants", {"price": "10", "optionValues": {"Contenance": "100 ml"}}, format="json")
    assert dup.status_code == 400 and "optionValues" in dup.json()["error"]["fields"]
    missing = api.post(f"{P}/{p.pk}/variants", {"price": "10"}, format="json")
    assert missing.status_code == 400
    wrong = api.post(f"{P}/{p.pk}/variants", {"price": "10", "optionValues": {"Contenance": "1 L"}}, format="json")
    assert wrong.status_code == 400

    in_use = api.put(f"{P}/{p.pk}/options", [{"name": "Contenance", "values": ["50 ml"]}], format="json")
    assert in_use.status_code == 409 and in_use.json()["error"]["code"] == "option_in_use"

    switch = api.patch(f"/api/v1/admin/variants/{big.json()['id']}", {"isDefault": True}, format="json")
    assert switch.json()["isDefault"]
    assert list(Variant.objects.filter(product=p, is_default=True).values_list("pk", flat=True)) == [big.json()["id"]]
    assert (
        p.status == "draft" and api.post(f"{P}/{p.pk}/status", {"status": "active"}, format="json").status_code == 200
    )


@pytest.mark.django_db
def test_ajout_d_option_complete_les_variantes_existantes(api, product):
    p = product(status="active")  # possible même sur un produit actif
    response = api.put(f"{P}/{p.pk}/options", [{"name": "Teinte", "values": ["Clair", "Foncé"]}], format="json")
    assert response.status_code == 200
    variant = api.get(f"{P}/{p.pk}").json()["variants"][0]
    assert variant["options"] == {"Teinte": "Clair"} and variant["title"] == "Clair"


@pytest.mark.django_db
def test_activation_exige_des_variantes_completes(api, product):
    from apps.catalog.models import ProductOption

    p = product()
    ProductOption.objects.create(product=p, name="Teinte").values.create(value="Clair")  # état incohérent forcé
    response = api.post(f"{P}/{p.pk}/status", {"status": "active"}, format="json")
    assert response.status_code == 400
    assert any("valeur pour chaque option" in e for e in response.json()["error"]["fields"]["status"])


@pytest.mark.django_db
def test_regles_de_prix_et_stock_en_lecture_seule(api, product):
    v = product().variants.get()
    url = f"/api/v1/admin/variants/{v.pk}"
    assert api.patch(url, {"compareAtPrice": "100"}, format="json").status_code == 400
    assert api.patch(url, {"compareAtPrice": "159.90"}, format="json").json()["compareAtPrice"] == 159.9
    assert api.patch(url, {"price": "12.345"}, format="json").status_code == 400  # 2 décimales max
    # Le stock ne se modifie JAMAIS ici (seulement par un mouvement de stock tracé).
    response = api.patch(url, {"stockQuantity": 999}, format="json")
    assert response.status_code == 200 and response.json()["stockQuantity"] == 10
    created = api.post(
        P, {"brand": "B", "name": "Nouveau", "variant": {"price": "10", "stockQuantity": 50}}, format="json"
    ).json()
    assert created["variants"][0]["stockQuantity"] is None  # jamais de stock inventé


@pytest.mark.django_db
def test_derniere_variante_non_supprimable_et_defaut_reattribue(api, product):
    p = product()
    first = p.variants.get()
    assert api.delete(f"/api/v1/admin/variants/{first.pk}").json()["error"]["code"] == "last_variant"
    second = api.post(f"{P}/{p.pk}/variants", {"price": "99"}, format="json")
    assert second.status_code == 201
    assert api.delete(f"/api/v1/admin/variants/{first.pk}").status_code == 204
    assert Variant.objects.get(pk=second.json()["id"]).is_default


@pytest.mark.django_db
def test_sku_doublon_refuse(api, product):
    a, b = product(slug="a").variants.get(), product(slug="b").variants.get()
    api.patch(f"/api/v1/admin/variants/{a.pk}", {"sku": "MPC-1"}, format="json")
    response = api.patch(f"/api/v1/admin/variants/{b.pk}", {"sku": "MPC-1"}, format="json")
    assert response.status_code == 400 and "sku" in response.json()["error"]["fields"]


# --- Images ---------------------------------------------------------------
@pytest.mark.django_db
def test_images_ajout_ordre_survol(api, product, media):
    p = product()
    first = p.images.get()
    second = api.post(
        f"{P}/{p.pk}/images",
        {"mediaId": media(color=(1, 1, 1)).pk, "alt": "Texture", "fit": "cover", "kind": "texture"},
        format="json",
    ).json()
    assert api.post(f"{P}/{p.pk}/images/reorder", {"ids": [second["id"], first.pk]}, format="json").status_code == 204
    assert list(p.images.order_by("position").values_list("pk", flat=True)) == [second["id"], first.pk]
    assert api.post(f"{P}/{p.pk}/images/reorder", {"ids": [first.pk]}, format="json").status_code == 400

    hover = api.patch(f"{P}/{p.pk}", {"hoverImageId": second["id"], "hoverImagePosition": "50% 88%"}, format="json")
    assert hover.status_code == 200 and hover.json()["hoverImageId"] == second["id"]
    assert api.patch(f"{P}/{p.pk}", {"hoverImagePosition": "milieu"}, format="json").status_code == 400


@pytest.mark.django_db
def test_image_d_un_autre_produit_refusee(api, product):
    a, b = product(slug="a"), product(slug="b")
    response = api.patch(f"{P}/{a.pk}", {"hoverImageId": b.images.get().pk}, format="json")
    assert response.status_code == 400 and "hoverImageId" in response.json()["error"]["fields"]


# --- Catégories -------------------------------------------------------
@pytest.mark.django_db
def test_categories_crud(api, product):
    created = api.post("/api/v1/admin/categories", {"name": "Soins du corps"}, format="json").json()
    assert created["slug"] == "soins-du-corps"
    used = product().categories.get()
    response = api.delete(f"/api/v1/admin/categories/{used.pk}")
    assert response.status_code == 409 and response.json()["error"]["code"] == "category_in_use"
    loop = api.patch(f"/api/v1/admin/categories/{created['id']}", {"parentId": created["id"]}, format="json")
    assert loop.status_code == 400
    ids = [c["id"] for c in api.get("/api/v1/admin/categories").json()]
    assert api.post("/api/v1/admin/categories/reorder", {"ids": list(reversed(ids))}, format="json").status_code == 204
