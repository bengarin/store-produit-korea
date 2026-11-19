"""Avis PRODUITS : dépôt, modération, API publique (approuvés seulement), achat vérifié, droits, données structurées."""

import json
import re

import pytest
from rest_framework.test import APIClient

from apps.accounts.roles import Role
from apps.audit.models import AuditLog
from apps.orders.models import Order
from apps.reviews.models import ProductReview, StoreReview
from tests.conftest import order_payload, post_order

STORE = "/api/v1/store"
ADMIN = "/api/v1/admin"


def review(**extra):
    data = {
        "name": "Salma",
        "rating": 4,
        "text": "Texture légère, ma peau est bien hydratée.",
        "language": "fr",
        "consent": True,
        "consentText": "J'accepte que mon prénom, ma note et mon avis soient publiés.",
    }
    data.update(extra)
    return data


@pytest.mark.django_db
def test_depot_en_attente_puis_approuve_et_public(client, staff, sellable):
    sellable(slug="creme-test")
    url = f"{STORE}/products/creme-test/reviews"
    r = client.post(url, review(), content_type="application/json")
    assert r.status_code == 201 and r.json() == {"ok": True, "status": "pending"}
    rv = ProductReview.objects.get()
    assert rv.status == "pending" and rv.product.slug == "creme-test" and rv.source == "customer"
    assert client.get(url).json() == {"count": 0, "average": None, "items": []}  # rien de public avant validation
    assert not StoreReview.objects.exists()  # séparé des avis sur la boutique
    api = staff(Role.CONTENT_EDITOR)
    listing = api.get(f"{ADMIN}/product-reviews?status=pending").json()
    assert listing["counts"] == {"pending": 1, "approved": 0, "rejected": 0}
    assert listing["items"][0]["productName"] and listing["items"][0]["verifiedPurchase"] is False
    r = api.patch(f"{ADMIN}/product-reviews/{rv.pk}", {"status": "approved"}, format="json")
    assert r.status_code == 200 and r.json()["approvedAt"] and r.json()["moderatedAt"]
    pub = client.get(url).json()
    assert pub["count"] == 1 and pub["average"] == 4.0
    assert set(pub["items"][0]) == {"id", "name", "rating", "text", "language", "date", "verifiedPurchase"}
    # Refus : retiré du public, conservé dans l'admin.
    api.patch(f"{ADMIN}/product-reviews/{rv.pk}", {"status": "rejected"}, format="json")
    assert client.get(url).json()["count"] == 0
    rv.refresh_from_db()
    assert rv.status == "rejected" and rv.approved_at is None and rv.moderated_at
    assert AuditLog.objects.filter(action__in=["product_review.approve", "product_review.reject"]).count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize(
    "bad",
    [
        {"rating": 0}, {"rating": 6}, {"rating": "cinq"}, {"consent": False}, {"text": "court"},
        {"text": "x" * 1001}, {"text": "Promo sur https://spam.example"}, {"text": "<script>alert(1)</script> super"},
        {"name": "<b>x</b>"}, {"name": " "},
    ],
)  # fmt: skip
def test_avis_invalides_refuses(client, sellable, bad):
    sellable(slug="creme-test")
    r = client.post(f"{STORE}/products/creme-test/reviews", review(**bad), content_type="application/json")
    assert r.status_code == 400
    assert not ProductReview.objects.exists()


@pytest.mark.django_db
def test_robot_doublon_produit_inconnu_ou_brouillon(client, sellable, product):
    sellable(slug="creme-test")
    url = f"{STORE}/products/creme-test/reviews"
    assert client.post(url, review(website="http://bot"), content_type="application/json").status_code == 201
    assert not ProductReview.objects.exists()  # champ piège : rien d'enregistré
    client.post(url, review(), content_type="application/json")
    client.post(url, review(), content_type="application/json")  # même texte renvoyé : un seul avis
    assert ProductReview.objects.count() == 1
    product(slug="brouillon", status="draft")
    assert (
        client.post(f"{STORE}/products/brouillon/reviews", review(), content_type="application/json").status_code == 404
    )
    assert client.get(f"{STORE}/products/inconnu/reviews").status_code == 404


@pytest.mark.django_db
def test_limite_de_debit(client, sellable, monkeypatch):
    from django.core.cache import cache
    from rest_framework.throttling import ScopedRateThrottle

    sellable(slug="creme-test")
    cache.clear()
    # Limite réduite pour ce test uniquement (remise en place automatiquement à la fin).
    monkeypatch.setattr(
        ScopedRateThrottle, "THROTTLE_RATES", {**ScopedRateThrottle.THROTTLE_RATES, "product_reviews": "2/hour"}
    )
    url = f"{STORE}/products/creme-test/reviews"
    codes = []
    for i in range(3):
        r = client.post(url, review(text=f"Très bon produit numéro {i}"), content_type="application/json")
        codes.append(r.status_code)
    assert codes == [201, 201, 429]
    assert ProductReview.objects.count() == 2
    cache.clear()


@pytest.mark.django_db
def test_achat_verifie_seulement_avec_commande_livree(client, staff, sellable):
    sellable(slug="creme-test", stock=10)
    sellable(slug="autre", stock=10)
    api = staff(Role.ADMIN)
    pid = ProductReview._meta.get_field("product").related_model.objects.get(slug="creme-test").pk
    number = post_order(APIClient(), order_payload([("creme-test", 1)])).json()["number"]
    other = post_order(APIClient(), order_payload([("autre", 1)], phone="06 98 76 54 32")).json()["number"]
    base = {
        "productId": pid, "name": "Nadia", "rating": 5, "text": "Reçu par WhatsApp : excellent produit.",
        "status": "approved", "sourceNote": "Message WhatsApp du 12/11", "attestation": True,
    }  # fmt: skip
    # Commande d'un autre produit : refusée.
    assert api.post(f"{ADMIN}/product-reviews", {**base, "orderNumber": other}, format="json").status_code == 400
    r = api.post(f"{ADMIN}/product-reviews", {**base, "orderNumber": number}, format="json")
    assert r.status_code == 201 and r.json()["source"] == "admin" and r.json()["order"] == number
    assert r.json()["verifiedPurchase"] is False  # commande pas encore livrée
    url = f"{STORE}/products/creme-test/reviews"
    assert client.get(url).json()["items"][0]["verifiedPurchase"] is False
    Order.objects.filter(number=number).update(status=Order.Status.DELIVERED)
    assert client.get(url).json()["items"][0]["verifiedPurchase"] is True
    Order.objects.filter(number=number).update(status=Order.Status.RETURNED)
    assert client.get(url).json()["items"][0]["verifiedPurchase"] is False


@pytest.mark.django_db
def test_saisie_manuelle_exige_attestation_et_provenance(staff, sellable):
    sellable(slug="creme-test")
    pid = ProductReview._meta.get_field("product").related_model.objects.get(slug="creme-test").pk
    api = staff(Role.ADMIN)
    base = {"productId": pid, "name": "Nadia", "rating": 5, "text": "Avis reçu par téléphone, très satisfaite."}
    r = api.post(f"{ADMIN}/product-reviews", {**base, "sourceNote": "Appel du 10/11"}, format="json")
    assert r.status_code == 400 and "attestation" in r.json()["error"]["fields"]
    r = api.post(f"{ADMIN}/product-reviews", {**base, "attestation": True}, format="json")
    assert r.status_code == 400 and "sourceNote" in r.json()["error"]["fields"]
    r = api.post(
        f"{ADMIN}/product-reviews", {**base, "attestation": True, "sourceNote": "Appel du 10/11"}, format="json"
    )
    assert r.status_code == 201 and r.json()["status"] == "pending"  # en attente par défaut
    assert ProductReview.objects.get().created_by == api.user


@pytest.mark.django_db
def test_filtres_admin_modification_et_droits(client, staff, sellable):
    a = sellable(slug="creme-a")
    sellable(slug="creme-b")
    for slug in ("creme-a", "creme-b"):
        client.post(
            f"{STORE}/products/{slug}/reviews",
            review(text=f"Avis sur {slug} vraiment top"),
            content_type="application/json",
        )
    editor = staff(Role.CONTENT_EDITOR)
    only_a = editor.get(f"{ADMIN}/product-reviews?product={a.pk}").json()
    assert only_a["total"] == 1 and only_a["items"][0]["productSlug"] == "creme-a"
    rid = only_a["items"][0]["id"]
    r = editor.patch(
        f"{ADMIN}/product-reviews/{rid}", {"text": "Avis corrigé : faute retirée.", "rating": 5}, format="json"
    )
    assert r.status_code == 200 and r.json()["rating"] == 5
    assert (
        editor.patch(f"{ADMIN}/product-reviews/{rid}", {"text": "<i>x</i> long texte"}, format="json").status_code
        == 400
    )
    for role in (Role.ANALYST, Role.ORDER_MANAGER):
        assert (
            staff(role).patch(f"{ADMIN}/product-reviews/{rid}", {"status": "approved"}, format="json").status_code
            == 403
        )
    assert editor.delete(f"{ADMIN}/product-reviews/{rid}").status_code == 403
    assert staff(Role.OWNER).delete(f"{ADMIN}/product-reviews/{rid}").status_code == 204
    assert client.get(f"{ADMIN}/product-reviews").status_code in (401, 403)
    assert ProductReview.objects.count() == 1


@pytest.mark.django_db
def test_fiche_produit_html_et_donnees_structurees(client, sellable, settings, tmp_path):
    (tmp_path / "index.html").write_text(
        '<html lang="fr"><head><title>x</title></head><body><div id="root"></div></body></html>'
    )
    settings.FRONTEND_DIST_DIR = tmp_path
    p = sellable(slug="creme-test")
    ProductReview.objects.create(product=p, name="Salma", rating=4, text="Très bien.", status="approved")
    ProductReview.objects.create(product=p, name="Robot", rating=1, text="En attente.", status="pending")
    html = client.get("/produits/creme-test").content.decode()
    ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
    assert ld["aggregateRating"]["ratingValue"] == 4.0 and ld["aggregateRating"]["reviewCount"] == 1
    assert [x["author"]["name"] for x in ld["review"]] == ["Salma"]
    root = html.split('<div id="root">')[1].split("</main>")[0]
    assert "Salma" in root and "Robot" not in root and "En attente" not in html


@pytest.mark.django_db
def test_note_des_cartes_avis_approuves_seulement(client, sellable):
    """Liste publique des produits : note et nombre d'avis APPROUVÉS seulement ; aucun champ sans avis approuvé."""
    p = sellable()
    other = sellable(slug="sans-avis")
    mk = lambda rating, status: ProductReview.objects.create(  # noqa: E731
        product=p, name="Salma", rating=rating, text="Texte d'avis suffisamment long.", status=status
    )
    mk(5, ProductReview.Status.PENDING)  # en attente : ignoré
    by_id = lambda: {x["id"]: x for x in client.get(f"{STORE}/products").json()["items"]}  # noqa: E731
    assert "reviews" not in by_id()[p.slug] and "reviews" not in by_id()[other.slug]
    mk(5, ProductReview.Status.APPROVED)
    mk(4, ProductReview.Status.APPROVED)
    mk(1, ProductReview.Status.REJECTED)  # refusé : ignoré
    assert by_id()[p.slug]["reviews"] == {"count": 2, "average": 4.5}
    assert "reviews" not in by_id()[other.slug]
    assert client.get(f"{STORE}/products/{p.slug}").json()["reviews"] == {"count": 2, "average": 4.5}
