"""Phase 6 — thème : validation (cas partagés avec le front), brouillon, publication, versions, permissions."""

import copy
import io
import json

import pytest
from openpyxl import load_workbook

from apps.accounts.roles import Role
from apps.audit.models import AuditLog
from apps.newsletter.models import Subscriber
from apps.themes.models import ThemeDraft, ThemeVersion
from apps.themes.validation import default_theme, shared_dir, validate_structure

A = "/api/v1/admin/theme"
STORE = "/api/v1/store/theme"
OWN, ADM, MGR, EDT, ANA = Role.OWNER, Role.ADMIN, Role.ORDER_MANAGER, Role.CONTENT_EDITOR, Role.ANALYST
CASES = json.loads((shared_dir() / "test-cases.json").read_text(encoding="utf-8"))["cases"]


def apply(theme, ops):
    for op in ops:
        *parents, last = op["path"]
        target = theme
        for key in parents:
            target = target[key]
        if op["op"] == "set":
            target[last] = copy.deepcopy(op["value"])
        elif op["op"] == "push":
            target[last].append(copy.deepcopy(op["value"]))
    return theme


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_cas_partages_avec_le_validateur_du_navigateur(case):
    _, errors = validate_structure(apply(default_theme(), case["ops"]))
    assert (not errors) == case["valid"], errors
    if not case["valid"]:
        assert case["path"] in errors, (case["path"], errors)


def test_theme_par_defaut_normalise_a_l_identique():
    value, errors = validate_structure(default_theme())
    assert errors == {} and value == default_theme()


def theme_with(**changes):
    t = default_theme()
    for path, value in changes.items():
        keys = [int(k) if k.isdigit() else k for k in path.split("__")]
        apply(t, [{"op": "set", "path": keys, "value": value}])
    return t


@pytest.fixture(autouse=True)
def _produits_du_theme_par_defaut(request):
    """Le thème par défaut cite 3 produits réels (le rituel) : ils doivent exister pour que le thème soit valide."""
    if "django_db" not in [m.name for m in request.node.iter_markers()]:
        return
    product = request.getfixturevalue("product")
    for slug in ("baroness-aloe-vera-gel", "some-by-mi-yuja-niacin-cream", "biovene-eye-patches"):
        product(slug=slug, status="active")


def save(api, data, revision):
    return api.put(f"{A}/draft", {"data": data, "revision": revision}, format="json")


@pytest.mark.django_db
def test_brouillon_enregistre_et_persistant(staff, client):
    api = staff(ADM)
    state = api.get(A).json()
    assert state["draft"]["revision"] == 1 and state["published"] is None and state["dirty"] is False
    data = default_theme()
    data["home"][0]["settings"]["heading"] = "Titre du brouillon"
    response = save(api, data, 1)
    assert response.status_code == 200, response.content
    again = api.get(A).json()  # « rechargement » : relu depuis MySQL
    assert (
        again["draft"]["revision"] == 2
        and again["draft"]["data"]["home"][0]["settings"]["heading"] == "Titre du brouillon"
    )
    assert again["dirty"] is True
    # La boutique publique ne voit JAMAIS le brouillon
    assert client.get(STORE).json() == {"version": None, "theme": None, "media": {}}
    assert AuditLog.objects.filter(action="theme.draft_save").exists()


@pytest.mark.django_db
def test_conflit_de_revision_aucun_ecrasement(staff):
    a, b = staff(ADM), staff(EDT)
    assert save(a, theme_with(home__0__settings__heading="Version A"), 1).status_code == 200
    stale = save(b, theme_with(home__0__settings__heading="Version B"), 1)  # B travaillait sur la révision 1
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "draft_conflict"
    assert ThemeDraft.objects.get().data["home"][0]["settings"]["heading"] == "Version A"


@pytest.mark.django_db
def test_brouillon_invalide_refuse_avec_chemins(staff):
    data = theme_with(home__0__settings__heading="<b>gras</b>", home__0__settings__buttonLink="javascript:alert(1)")
    api = staff(ADM)
    response = save(api, data, 1)
    fields = response.json()["error"]["fields"]
    assert response.status_code == 400
    assert "home.0.settings.heading" in fields and "home.0.settings.buttonLink" in fields
    assert api.get(A).json()["draft"]["revision"] == 1  # rien d'enregistré


@pytest.mark.django_db
def test_references_verifiees_en_base(staff, media, product):
    api = staff(ADM)
    m = media()
    product(slug="existe")
    ok = theme_with(home__0__settings__imageDesktop={"mediaId": m.pk}, home__1__items__0__product="existe")
    assert save(api, ok, 1).status_code == 200
    bad = theme_with(home__0__settings__imageDesktop={"mediaId": 999999}, home__1__items__0__product="inconnu")
    bad["home"][4]["settings"]["category"] = "fantome"
    fields = save(api, bad, 2).json()["error"]["fields"]
    assert set(fields) >= {"home.0.settings.imageDesktop", "home.1.items.0.product", "home.4.settings.category"}


@pytest.mark.django_db
def test_taille_maximale(staff):
    data = default_theme()
    data["home"] += [{"id": f"s{i}", "type": "image_with_text", "settings": {"heading": "x"}} for i in range(4)]
    data["settings"]["junk"] = "x" * 300_000
    response = save(staff(ADM), data, 1)
    assert response.status_code == 400


@pytest.mark.django_db
def test_publication_restauration_et_historique(staff, client, media):
    api = staff(ADM)
    m = media()
    v1 = theme_with(home__0__settings__heading="Version 1", home__0__settings__imageDesktop={"mediaId": m.pk})
    save(api, v1, 1)
    published = api.post(f"{A}/publish", {"revision": 2, "note": "Lancement"}, format="json")
    assert published.status_code == 201 and published.json()["publishedNumber"] == 1
    public = client.get(STORE).json()
    assert public["version"] == 1 and public["theme"]["home"][0]["settings"]["heading"] == "Version 1"
    assert public["media"][str(m.pk)]["src"].endswith(".webp")
    assert "revision" not in json.dumps(public) and "updatedBy" not in json.dumps(public)

    # Rien de nouveau : on ne republie pas la même chose
    again = api.post(f"{A}/publish", {"revision": 2}, format="json")
    assert again.status_code == 409 and again.json()["error"]["code"] == "nothing_to_publish"

    save(api, theme_with(home__0__settings__heading="Version 2"), 2)
    # Le brouillon modifié n'est PAS publié tant qu'on ne publie pas
    assert client.get(STORE).json()["theme"]["home"][0]["settings"]["heading"] == "Version 1"
    # Publier une révision périmée est refusé (le brouillon a changé depuis l'affichage)
    assert api.post(f"{A}/publish", {"revision": 2}, format="json").status_code == 409
    assert api.post(f"{A}/publish", {"revision": 3}, format="json").json()["publishedNumber"] == 2
    assert client.get(STORE).json()["theme"]["home"][0]["settings"]["heading"] == "Version 2"

    # Restaurer la version 1 = nouvelle version 3 identique à la 1 ; l'historique est conservé
    restored = api.post(f"{A}/versions/1/restore", format="json")
    assert restored.status_code == 201 and restored.json()["publishedNumber"] == 3
    assert client.get(STORE).json()["theme"]["home"][0]["settings"]["heading"] == "Version 1"
    history = api.get(f"{A}/versions").json()["items"]
    assert [(v["number"], v["source"], v["restoredFrom"], v["isCurrent"]) for v in history] == [
        (3, "restore", 1, True),
        (2, "publish", None, False),
        (1, "publish", None, False),
    ]
    assert ThemeVersion.objects.get(number=3).checksum == ThemeVersion.objects.get(number=1).checksum
    assert api.post(f"{A}/versions/3/restore", format="json").status_code == 409  # déjà publiée
    # Le brouillon n'a pas bougé (Version 2) : l'écran le signale comme différent
    state = api.get(A).json()
    assert state["draft"]["data"]["home"][0]["settings"]["heading"] == "Version 2" and state["dirty"] is True

    # Charger une version dans le brouillon (sans publier)
    loaded = api.post(f"{A}/versions/1/load", {"revision": 3}, format="json")
    assert loaded.status_code == 200 and loaded.json()["draft"]["data"]["home"][0]["settings"]["heading"] == "Version 1"
    assert loaded.json()["dirty"] is False
    assert AuditLog.objects.filter(action__in=["theme.publish", "theme.restore", "theme.draft_load"]).count() == 4


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,read,edit,publish",
    [
        (OWN, 200, 200, 201),
        (ADM, 200, 200, 201),
        (EDT, 200, 200, 403),
        (MGR, 200, 403, 403),
        (ANA, 200, 403, 403),
        (None, 403, 403, 403),
    ],
)
def test_permissions_cinq_roles(staff, role, read, edit, publish):
    api = staff(role)
    assert api.get(A).status_code == read
    assert api.get(f"{A}/versions").status_code == read
    assert save(api, theme_with(home__0__settings__heading="Essai"), 1).status_code == edit
    rev = ThemeDraft.objects.get().revision if ThemeDraft.objects.exists() else 1
    response = api.post(f"{A}/publish", {"revision": rev}, format="json")
    assert response.status_code == publish
    if publish == 201:
        assert api.post(f"{A}/versions/1/restore", format="json").status_code == 409  # déjà publiée, mais autorisé
    else:
        assert api.post(f"{A}/versions/1/restore", format="json").status_code in (403, 404)
        assert not ThemeVersion.objects.exists()
    if read == 200:
        state = api.get(A).json()
        assert state["canEdit"] == (edit == 200) and state["canPublish"] == (publish == 201)


@pytest.mark.django_db
def test_anonyme_et_session_absente(client):
    assert client.get(A).status_code == 403
    assert client.put(f"{A}/draft", {"data": default_theme(), "revision": 1}, format="json").status_code == 403
    assert client.get(STORE).status_code == 200


@pytest.mark.django_db
def test_media_utilise_par_le_theme_non_supprimable(staff, media):
    api = staff(ADM)
    m = media()
    save(api, theme_with(home__0__settings__imageDesktop={"mediaId": m.pk}), 1)
    response = api.delete(f"/api/v1/admin/media/{m.pk}")
    assert response.status_code == 409 and response.json()["error"]["code"] == "media_in_use"
    # Encore référencée par une version publiée après avoir été retirée du brouillon : toujours protégée
    api.post(f"{A}/publish", {"revision": 2}, format="json")
    save(api, default_theme(), 2)
    assert api.delete(f"/api/v1/admin/media/{m.pk}").status_code == 409


@pytest.mark.django_db
def test_newsletter_inscription_consentement_et_droits(client, staff):
    url = "/api/v1/store/newsletter"
    body = {"email": "Lina@Exemple.ma", "consent": True, "consentText": "J'accepte.", "website": ""}
    assert client.post(url, body, format="json").status_code == 201
    assert client.post(url, body, format="json").status_code == 201  # même réponse : rien n'est divulgué
    assert Subscriber.objects.get().email == "lina@exemple.ma" and Subscriber.objects.count() == 1
    assert client.post(url, {**body, "consent": False, "email": "b@exemple.ma"}, format="json").status_code == 400
    assert client.post(url, {**body, "email": "pas-un-email"}, format="json").status_code == 400
    assert client.post(url, {**body, "email": "robot@exemple.ma", "website": "spam"}, format="json").status_code == 201
    assert not Subscriber.objects.filter(email="robot@exemple.ma").exists()  # champ piège : rien enregistré
    apis = {role: staff(role) for role in (OWN, ADM, MGR, EDT, ANA, None)}
    for role, code in ((OWN, 200), (ADM, 200), (MGR, 403), (EDT, 403), (ANA, 403), (None, 403)):
        assert apis[role].get("/api/v1/admin/newsletter/subscribers").status_code == code
        assert apis[role].get("/api/v1/admin/newsletter/export").status_code == code
    response = apis[ADM].get("/api/v1/admin/newsletter/export")
    rows = list(load_workbook(io.BytesIO(response.content))["Inscrits"].iter_rows(values_only=True))
    assert rows[1][0] == "lina@exemple.ma" and rows[1][2] == "J'accepte."
