"""Blog (articles FR/AR, brouillon/publié, admin) et avis sur la boutique (dépôt, modération, droits)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.roles import Role
from apps.audit.models import AuditLog
from apps.blog.models import Article
from apps.reviews.models import StoreReview

STORE = "/api/v1/store"
ADMIN = "/api/v1/admin"


# --- Blog ------------------------------------------------------------------------
@pytest.mark.django_db
def test_article_brouillon_invisible_puis_publie(client, staff, media):
    api = staff(Role.CONTENT_EDITOR)
    cover = media()
    r = api.post(
        f"{ADMIN}/blog/articles",
        {
            "title": "Routine du soir en 4 étapes",
            "titleAr": "روتين المساء",
            "excerpt": "Démaquiller, nettoyer, hydrater.",
            "bodyHtml": "<p>Texte <script>alert(1)</script><strong>gras</strong></p>",
            "coverId": cover.pk,
        },
        format="json",
    )
    assert r.status_code == 201, r.json()
    art = r.json()
    assert art["slug"] == "routine-du-soir-en-4-etapes"
    assert art["status"] == "draft" and art["publishedAt"] is None
    assert "<script>" not in art["bodyHtml"] and "<strong>gras</strong>" in art["bodyHtml"]
    # Brouillon : ni dans la liste ni en accès direct.
    assert client.get(f"{STORE}/blog").json()["items"] == []
    assert client.get(f"{STORE}/blog/{art['slug']}").status_code == 404
    # Publier : date de publication posée automatiquement.
    r = api.patch(f"{ADMIN}/blog/articles/{art['id']}", {"status": "published"}, format="json")
    assert r.status_code == 200 and r.json()["publishedAt"]
    items = client.get(f"{STORE}/blog").json()["items"]
    assert [i["slug"] for i in items] == [art["slug"]]
    assert "bodyHtml" not in items[0]  # la liste ne transporte pas le texte complet
    assert items[0]["cover"]["src"] and items[0]["translations"] == {"ar": {"title": "روتين المساء"}}
    full = client.get(f"{STORE}/blog/{art['slug']}").json()
    assert "<strong>gras</strong>" in full["bodyHtml"]
    assert AuditLog.objects.filter(action__in=["blog.create", "blog.update"]).count() == 2


@pytest.mark.django_db
def test_publication_programmee_et_ordre(client, staff):
    api = staff(Role.ADMIN)
    now = timezone.now()
    for title, delta in (("Ancien", -5), ("Récent", -1), ("Futur", 3)):
        api.post(
            f"{ADMIN}/blog/articles",
            {"title": title, "bodyHtml": "<p>x</p>", "status": "published",
             "publishedAt": (now + timedelta(days=delta)).isoformat()},
            format="json",
        )  # fmt: skip
    assert [i["title"] for i in client.get(f"{STORE}/blog").json()["items"]] == ["Récent", "Ancien"]


@pytest.mark.django_db
def test_publier_sans_texte_refuse_et_adresse_unique(staff):
    api = staff(Role.ADMIN)
    r = api.post(f"{ADMIN}/blog/articles", {"title": "Vide", "status": "published"}, format="json")
    assert r.status_code == 400
    a = api.post(f"{ADMIN}/blog/articles", {"title": "Même titre"}, format="json").json()
    b = api.post(f"{ADMIN}/blog/articles", {"title": "Même titre"}, format="json").json()
    assert a["slug"] != b["slug"]
    r = api.patch(f"{ADMIN}/blog/articles/{b['id']}", {"slug": a["slug"]}, format="json")
    assert r.status_code == 400


@pytest.mark.django_db
def test_droits_blog(staff):
    analyst = staff(Role.ANALYST)
    assert analyst.get(f"{ADMIN}/blog/articles").status_code == 200
    assert analyst.post(f"{ADMIN}/blog/articles", {"title": "x"}, format="json").status_code == 403
    editor = staff(Role.CONTENT_EDITOR)
    art = editor.post(f"{ADMIN}/blog/articles", {"title": "À supprimer"}, format="json").json()
    assert editor.delete(f"{ADMIN}/blog/articles/{art['id']}").status_code == 403
    assert staff(Role.OWNER).delete(f"{ADMIN}/blog/articles/{art['id']}").status_code == 204
    assert not Article.objects.exists()


# --- Avis sur la boutique ------------------------------------------------------------
def review(**extra):
    data = {
        "name": "Salma",
        "rating": 5,
        "text": "Livraison rapide et produits bien emballés.",
        "consent": True,
        "consentText": "J'accepte que mon prénom et mon avis soient publiés.",
    }
    data.update(extra)
    return data


@pytest.mark.django_db
def test_avis_en_attente_puis_approuve(client, staff):
    r = client.post(f"{STORE}/reviews", review(), content_type="application/json")
    assert r.status_code == 201 and r.json()["status"] == "pending"
    assert client.get(f"{STORE}/reviews").json() == {"count": 0, "average": None, "items": []}
    api = staff(Role.CONTENT_EDITOR)
    listing = api.get(f"{ADMIN}/reviews?status=pending").json()
    assert listing["counts"] == {"pending": 1, "approved": 0}
    rid = listing["items"][0]["id"]
    # Corriger une faute puis approuver.
    r = api.patch(f"{ADMIN}/reviews/{rid}", {"text": "Livraison rapide, produits bien emballés.", "status": "approved"},
                  format="json")  # fmt: skip
    assert r.status_code == 200 and r.json()["approvedAt"]
    client.post(f"{STORE}/reviews", review(name="Youssef", rating=3), content_type="application/json")
    StoreReview.objects.filter(name="Youssef").update(status="approved", approved_at=timezone.now())
    pub = client.get(f"{STORE}/reviews").json()
    assert pub["count"] == 2 and pub["average"] == 4.0
    item = next(i for i in pub["items"] if i["name"] == "Salma")
    assert set(item) == {"id", "name", "rating", "text", "language", "date"}  # rien de privé
    assert item["text"] == "Livraison rapide, produits bien emballés."
    # Dépublier : retiré de la boutique.
    api.patch(f"{ADMIN}/reviews/{rid}", {"status": "pending"}, format="json")
    assert client.get(f"{STORE}/reviews").json()["count"] == 1
    assert AuditLog.objects.filter(action="review.approve").count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "bad",
    [
        {"rating": 0},
        {"rating": 6},
        {"consent": False},
        {"text": "court"},
        {"text": "Allez voir https://spam.example pour des promos"},
        {"name": "<b>x</b>"},
        {"name": " "},
    ],
)
def test_avis_invalides_refuses(client, bad):
    assert client.post(f"{STORE}/reviews", review(**bad), content_type="application/json").status_code == 400
    assert not StoreReview.objects.exists()


@pytest.mark.django_db
def test_avis_robot_ignore_sans_le_dire(client):
    r = client.post(f"{STORE}/reviews", review(website="http://bot"), content_type="application/json")
    assert r.status_code == 201
    assert not StoreReview.objects.exists()


@pytest.mark.django_db
def test_droits_moderation(client, staff):
    client.post(f"{STORE}/reviews", review(), content_type="application/json")
    rid = StoreReview.objects.get().pk
    assert client.get(f"{ADMIN}/reviews").status_code in (401, 403)
    for role in (Role.ANALYST, Role.ORDER_MANAGER):
        r = staff(role).patch(f"{ADMIN}/reviews/{rid}", {"status": "approved"}, format="json")
        assert r.status_code == 403
    assert staff(Role.CONTENT_EDITOR).delete(f"{ADMIN}/reviews/{rid}").status_code == 403
    assert staff(Role.ADMIN).delete(f"{ADMIN}/reviews/{rid}").status_code == 204
    assert not StoreReview.objects.exists()
