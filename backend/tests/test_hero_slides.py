"""Bannière d'accueil : diapositives gérées dans Visuels marketing (ajout, modification, ordre, publication)."""

import pytest

from apps.accounts.roles import Role
from apps.media_library.models import MediaAsset
from apps.themes.hero import slide_from_theme_settings
from apps.themes.models import HeroSlide
from apps.themes.validation import default_theme

A = "/api/v1/admin/hero-slides"
STORE = "/api/v1/store/theme"


@pytest.fixture(autouse=True)
def _seed(db):
    """Même fonction que la migration (la base peut avoir été vidée par un test de concurrence)."""
    import importlib

    from django.apps import apps as django_apps

    importlib.import_module("apps.themes.migrations.0003_seed_first_hero_slide").seed(django_apps, None)


def new_slide(api, media, **data):
    body = {"titleFr": "Nouveautés", "desktopMediaId": media(color=(data.pop("c", 9), 9, 9)).pk, **data}
    return api.post(A, body, format="json")


@pytest.mark.django_db
def test_banniere_actuelle_devient_la_premiere_diapositive(client):
    # Créée par la migration à partir du thème : mêmes textes, mêmes visuels d'origine, même lien.
    slide = HeroSlide.objects.get()
    hero = next(s for s in default_theme()["home"] if s["type"] == "hero")["settings"]
    assert slide.position == 0 and slide.is_active
    assert slide.title_fr == hero["heading"] and slide.button_link == hero["buttonLink"]
    assert (slide.desktop_asset, slide.mobile_asset) == ("hero-wide", "hero-portrait")
    assert slide.title_ar == "عناية لطيفة لبشرة أجمل كل يوم"
    data = client.get(STORE).json()
    assert [s["title"]["fr"] for s in data["heroSlides"]] == [hero["heading"]]
    assert data["heroSlides"][0]["imageDesktop"] == {"asset": "hero-wide"}


@pytest.mark.django_db
def test_reprend_un_texte_modifie_sans_traduction_arabe_inventee():
    fields = slide_from_theme_settings({"heading": "Promo été", "imageDesktop": {"mediaId": 4}})
    assert fields["title_fr"] == "Promo été" and fields["title_ar"] == ""
    assert fields["desktop_media_id"] == 4 and fields["desktop_asset"] == ""


@pytest.mark.django_db
def test_ajout_ordre_publication_suppression(client, staff, media):
    api = staff(Role.CONTENT_EDITOR)
    first = HeroSlide.objects.get().pk
    a = new_slide(api, media, titleAr="جديدنا", buttonLabelFr="Voir", buttonLink="/produits", c=1)
    assert a.status_code == 201, a.content
    a = a.json()
    m = media(color=(1, 2, 3))
    b = new_slide(api, media, mobileMediaId=m.pk, textFr="Texte", c=2).json()
    assert [a["position"], b["position"]] == [1, 2]
    assert b["mobile"]["id"] == m.pk

    order = [b["id"], first, a["id"]]
    assert api.post(f"{A}/reorder", {"ids": order}, format="json").status_code == 204
    assert [s["id"] for s in client.get(STORE).json()["heroSlides"]] == order

    # Dépublier : disparaît de la boutique, reste dans l'admin.
    assert api.patch(f"{A}/{first}", {"isActive": False}, format="json").json()["isActive"] is False
    public = client.get(STORE).json()
    assert [s["id"] for s in public["heroSlides"]] == [b["id"], a["id"]]
    assert str(m.pk) in public["media"]  # images de la médiathèque jointes
    assert len(api.get(A).json()["items"]) == 3

    # Supprimer : seule l'Admin / le Propriétaire peut ; l'image reste dans la médiathèque.
    assert api.delete(f"{A}/{a['id']}").status_code == 403
    assert staff(Role.ADMIN).delete(f"{A}/{a['id']}").status_code == 204
    assert MediaAsset.objects.filter(pk=a["desktopMediaId"]).exists()
    assert not HeroSlide.objects.filter(pk=a["id"]).exists()


@pytest.mark.django_db
def test_remplacer_image_et_retirer_mobile(staff, media):
    api = staff()
    slide = HeroSlide.objects.get()
    m = media(color=(5, 5, 5))
    r = api.patch(f"{A}/{slide.pk}", {"desktopMediaId": m.pk, "mobileAsset": ""}, format="json").json()
    assert r["desktopMediaId"] == m.pk and r["desktopAsset"] == "" and r["mobileAsset"] == ""
    # Image utilisée par une diapositive : la médiathèque refuse de la supprimer.
    assert api.delete(f"/api/v1/admin/media/{m.pk}").status_code == 409


@pytest.mark.django_db
@pytest.mark.parametrize(
    "body,field",
    [
        ({"titleFr": ""}, "titleFr"),
        ({"titleFr": "<b>x</b>"}, "titleFr"),
        ({"buttonLink": "javascript:alert(1)"}, "buttonLink"),
        ({"buttonLink": "", "buttonLabelFr": "Voir"}, "buttonLink"),
        ({"desktopAsset": "../../etc"}, "desktopAsset"),
        ({"desktopAsset": "", "desktopMediaId": None}, "desktopMediaId"),
        ({"titleAr": "x" * 121}, "titleAr"),
    ],
)
def test_validation(staff, body, field):
    slide = HeroSlide.objects.get()
    r = staff().patch(f"{A}/{slide.pk}", body, format="json")
    assert r.status_code == 400 and field in r.json()["error"]["fields"], r.content


@pytest.mark.django_db
def test_permissions_et_reorder_invalide(client, staff, media):
    assert client.get(A).status_code in (401, 403)
    assert staff(Role.ANALYST).post(A, {"titleFr": "x"}, format="json").status_code == 403
    first = HeroSlide.objects.get().pk
    api = staff()
    assert api.post(f"{A}/reorder", {"ids": [first, first]}, format="json").status_code == 400
    assert api.post(f"{A}/reorder", {"ids": [first, 99999]}, format="json").status_code == 400


@pytest.mark.django_db
def test_donnees_jointes_a_la_page(client):
    from apps.seo.bootstrap import store_data

    assert store_data(products=[])["theme"]["heroSlides"][0]["id"] == HeroSlide.objects.get().pk
