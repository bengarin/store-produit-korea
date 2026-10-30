"""Phase 4 : aperçu, duplication, recherche, sécurité de la description."""

from decimal import Decimal

import pytest

from apps.accounts.roles import Role
from apps.audit.models import AuditLog
from apps.catalog.models import ProductOptionValue, Variant

P = "/api/v1/admin/products"
OWN, A, M, E, N = Role.OWNER, Role.ADMIN, Role.ORDER_MANAGER, Role.CONTENT_EDITOR, Role.ANALYST


@pytest.mark.django_db
def test_apercu_identique_au_format_public(staff, client, product):
    p = product(status="active")
    preview = staff().get(f"{P}/{p.pk}/preview").json()
    public = client.get(f"/api/v1/store/products/{p.slug}").json()
    assert preview["product"] == public  # même fonction, même format
    assert preview["status"] == "active" and preview["activationErrors"] == []
    assert preview["categoryLabels"][public["categories"][0]] == f"Cat {p.slug}"


@pytest.mark.django_db
def test_apercu_d_un_brouillon_reserve_a_l_equipe(staff, client, product):
    p = product(slug="brouillon")
    assert client.get("/api/v1/store/products/brouillon").status_code == 404
    data = staff(E).get(f"{P}/{p.pk}/preview").json()
    assert data["status"] == "draft" and data["product"]["id"] == "brouillon"
    assert "cost" not in str(data) and "40.00" not in str(data)
    assert client.get(f"{P}/{p.pk}/preview").status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("role,code", [(OWN, 200), (A, 200), (M, 200), (E, 200), (N, 200), (None, 403)])
def test_apercu_permissions(staff, product, role, code):
    assert staff(role).get(f"{P}/{product().pk}/preview").status_code == code


@pytest.mark.django_db
def test_duplication_complete_sans_stock(staff, product, media):
    p = product(status="active")
    api = staff()
    api.put(f"{P}/{p.pk}/options", [{"name": "Contenance", "values": ["50 ml", "100 ml"]}], format="json")
    default = p.variants.get()
    api.patch(
        f"/api/v1/admin/variants/{default.pk}",
        {"optionValues": {"Contenance": "50 ml"}, "sku": "SKU-50", "barcode": "611000000001"},
        format="json",
    )
    api.post(f"{P}/{p.pk}/variants", {"price": "199", "optionValues": {"Contenance": "100 ml"}}, format="json")
    second = api.post(
        f"{P}/{p.pk}/images", {"mediaId": media(color=(9, 8, 7)).pk, "alt": "Texture"}, format="json"
    ).json()
    api.patch(f"{P}/{p.pk}", {"hoverImageId": second["id"], "hoverImagePosition": "50% 80%"}, format="json")

    response = api.post(f"{P}/{p.pk}/duplicate")
    assert response.status_code == 201, response.content
    copy = response.json()
    assert copy["status"] == "draft" and copy["slug"] == "creme-test-copie" and copy["publishedAt"] is None
    assert copy["displayName"] == "Marque Crème test (copie)"
    variants = {tuple(v["options"].values()): v for v in copy["variants"]}
    assert set(variants) == {("50 ml",), ("100 ml",)}
    assert all(v["stockQuantity"] is None and v["sku"] is None and v["barcode"] is None for v in copy["variants"])
    assert variants[("100 ml",)]["price"] == 199.0 and variants[("50 ml",)]["cost"] == 40.0
    assert [i["mediaId"] for i in copy["images"]] == [i.media_id for i in p.images.order_by("position")]
    assert copy["hoverImageId"] != second["id"]  # pointe vers l'image de la COPIE
    assert copy["hoverImageId"] in [i["id"] for i in copy["images"]]
    assert copy["categories"] == [{"id": c.pk, "slug": c.slug, "name": c.name} for c in p.categories.all()]
    # L'original est intact, et la copie peut être activée (elle est complète)
    assert Variant.objects.filter(product=p).values_list("sku", flat=True).first() == "SKU-50"
    assert api.post(f"{P}/{copy['id']}/status", {"status": "active"}, format="json").status_code == 200
    assert AuditLog.objects.filter(action="product.duplicate").exists()
    assert ProductOptionValue.objects.filter(option__product_id=copy["id"]).count() == 2


@pytest.mark.django_db
def test_duplication_ne_copie_jamais_le_stock(staff, product):
    p = product()
    Variant.objects.filter(product=p).update(stock_quantity=42)
    copy = staff().post(f"{P}/{p.pk}/duplicate").json()
    assert copy["variants"][0]["stockQuantity"] is None
    assert Variant.objects.get(product=p).stock_quantity == 42


@pytest.mark.django_db
@pytest.mark.parametrize("role,code", [(OWN, 201), (A, 201), (E, 201), (M, 403), (N, 403), (None, 403)])
def test_duplication_permissions(staff, product, role, code):
    p = product()
    assert staff(role).post(f"{P}/{p.pk}/duplicate").status_code == code


@pytest.mark.django_db
def test_recherche_nom_sku_reference(staff, product):
    a, b = product(slug="aloe-gel"), product(slug="yuja-creme")
    Variant.objects.filter(product=a).update(sku="MPC-ALOE-01", barcode="6111234567890")
    api = staff(N)
    for term, expected in (("ALOE-0", "aloe-gel"), ("6111234567890", "aloe-gel"), ("yuja", "yuja-creme")):
        assert [p["slug"] for p in api.get(f"{P}?search={term}").json()["items"]] == [expected], term
    item = api.get(f"{P}?search=aloe").json()["items"][0]
    assert item["sku"] == "MPC-ALOE-01" and item["stockUnknown"] == 0 and item["totalStock"] == 10
    Variant.objects.filter(product=b).update(stock_quantity=None)
    item = api.get(f"{P}?search=yuja").json()["items"][0]
    assert item["stockUnknown"] == 1 and item["totalStock"] is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "html,forbidden",
    [
        ('<img src=x onerror="alert(1)">', ["<img", "onerror"]),
        ('<iframe src="https://evil.example"></iframe>', ["<iframe"]),
        ('<p style="position:fixed">x</p>', ["style="]),
        ('<svg onload="alert(1)"><circle/></svg>', ["<svg", "onload"]),
        ('<a href="data:text/html;base64,PHNjcmlwdD4=">x</a>', ["data:"]),
        ('<a href="JaVaScRiPt:alert(1)">x</a>', ["javascript:", "JaVaScRiPt"]),
        ("<script>alert(1)</script><p>ok</p>", ["<script", "alert"]),
        ('<form action="/x"><input name="a"></form>', ["<form", "<input"]),
    ],
)
def test_description_longue_jamais_de_html_dangereux(staff, product, html, forbidden):
    p = product()
    saved = staff(E).patch(f"{P}/{p.pk}", {"descriptionHtml": html}, format="json").json()["descriptionHtml"]
    for token in forbidden:
        assert token.lower() not in saved.lower(), (html, saved)


@pytest.mark.django_db
def test_description_longue_garde_la_mise_en_forme_autorisee(staff, product):
    p = product()
    html = (
        "<h2>Titre</h2><p><strong>Gras</strong> et <em>italique</em></p><ul><li>Un</li></ul>"
        '<ol><li>Deux</li></ol><p><a href="https://exemple.ma">lien</a></p>'
    )
    api = staff()
    saved = api.patch(f"{P}/{p.pk}", {"descriptionHtml": html}, format="json").json()["descriptionHtml"]
    for tag in ("<h2>", "<strong>", "<em>", "<ul>", "<ol>", 'href="https://exemple.ma"', 'rel="noopener noreferrer'):
        assert tag in saved
    public = api.get(f"{P}/{p.pk}/preview").json()["product"]
    assert public["descriptionHtml"] == saved


@pytest.mark.django_db
def test_editeur_ne_voit_ni_ne_modifie_le_cout_dans_l_editeur(staff, product):
    p = product()
    editor = staff(E)
    detail = editor.get(f"{P}/{p.pk}").json()
    assert "cost" not in detail["variants"][0]
    created = editor.post(f"{P}/{p.pk}/variants", {"price": "50", "cost": "10"}, format="json")
    assert created.status_code == 400 and "cost" in created.json()["error"]["fields"]
    assert Variant.objects.filter(product=p, cost=Decimal("10")).count() == 0


@pytest.mark.django_db
def test_suppression_d_un_brouillon_avec_options(staff, product):
    """Régression : un brouillon avec options et variantes se supprime (avant : erreur 500)."""
    p = product()
    api = staff()
    api.put(f"{P}/{p.pk}/options", [{"name": "Contenance", "values": ["50 ml", "100 ml"]}], format="json")
    api.post(f"{P}/{p.pk}/variants", {"price": "199", "optionValues": {"Contenance": "100 ml"}}, format="json")
    assert Variant.objects.filter(product=p).count() == 2
    response = api.delete(f"{P}/{p.pk}")
    assert response.status_code == 204, response.content
    assert not Variant.objects.filter(product_id=p.pk).exists()
    assert not ProductOptionValue.objects.filter(option__product_id=p.pk).exists()
