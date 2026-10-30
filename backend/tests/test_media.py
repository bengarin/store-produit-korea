"""Sécurité des téléversements d'images."""

import io

import pytest
from PIL import Image

from apps.media_library.models import MediaAsset
from tests.conftest import image_bytes, upload

URL = "/api/v1/admin/media"


@pytest.fixture
def api(staff):
    return staff()


def post(api, file):
    return api.post(URL, {"file": file, "alt": "Photo"}, format="multipart")


def assert_rejected(response):
    assert response.status_code == 400, response.content
    assert "file" in response.json()["error"]["fields"]
    assert MediaAsset.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_formats_acceptes_et_reencodes_en_webp(api, settings, fmt):
    response = post(api, upload(f"photo.{fmt.lower()}", image_bytes(fmt, size=(2400, 1800))))
    assert response.status_code == 201, response.content
    data = response.json()
    assert data["mimeType"] == "image/webp" and data["url"].endswith(".webp")
    assert (data["width"], data["height"]) == (1600, 1200)  # réduite à 1600 px
    asset = MediaAsset.objects.get()
    with Image.open(asset.file.path) as img:
        assert img.format == "WEBP"
    with Image.open(asset.file_640.path) as small:
        assert small.width == 640
    assert data["originalFilename"] == f"photo.{fmt.lower()}"


@pytest.mark.django_db
def test_metadonnees_gps_supprimees(api):
    exif = Image.Exif()
    exif[0x8825] = {2: (33.0, 35.0, 0.0)}  # GPS
    exif[0x010F] = "Appareil secret"
    data = image_bytes("JPEG", exif=exif.tobytes())
    with Image.open(io.BytesIO(data)) as original:
        assert original.getexif()  # l'original contient bien des métadonnées
    post(api, upload("gps.jpg", data, "image/jpeg"))
    with Image.open(MediaAsset.objects.get().file.path) as stored:
        assert not stored.getexif()
        assert "exif" not in stored.info


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name,data,content_type",
    [
        ("faux.jpg", b"Ceci n'est pas une image", "image/jpeg"),
        ("page.png", b"<html><script>alert(1)</script></html>", "image/png"),
        ("logo.svg", b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>', "image/svg+xml"),
        ("anim.gif", None, "image/gif"),
        ("vide.png", b"", "image/png"),
    ],
)
def test_fichiers_non_images_refuses(api, name, data, content_type):
    if data is None:
        data = image_bytes("GIF")
    assert_rejected(post(api, upload(name, data, content_type)))


@pytest.mark.django_db
def test_image_tronquee_refusee(api):
    data = image_bytes("PNG", size=(900, 900))
    assert_rejected(post(api, upload("coupee.png", data[: len(data) // 2])))


@pytest.mark.django_db
def test_trop_lourde_refusee(api, settings):
    settings.MEDIA_MAX_UPLOAD_BYTES = 1000
    assert_rejected(post(api, upload("lourde.png", image_bytes(size=(900, 900)))))


@pytest.mark.django_db
def test_dimensions_hors_limites(api, settings):
    settings.MEDIA_MAX_SIDE = 1000
    assert_rejected(post(api, upload("grande.png", image_bytes(size=(1200, 800)))))
    assert_rejected(post(api, upload("mini.png", image_bytes(size=(50, 50)))))


@pytest.mark.django_db
def test_bombe_de_decompression_refusee(api, settings):
    settings.MEDIA_MAX_SIDE = 1000  # surface max 1 Mpx
    bomb = image_bytes("PNG", size=(3000, 3000), color=(0, 0, 0))  # compresse très bien, 9 Mpx une fois décodée
    assert len(bomb) < 100_000
    assert_rejected(post(api, upload("bombe.png", bomb)))


@pytest.mark.django_db
def test_doublon_renvoie_le_meme_media(api):
    data = image_bytes()
    first = post(api, upload("a.png", data))
    second = post(api, upload("b.png", data))
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"] and MediaAsset.objects.count() == 1


@pytest.mark.django_db
def test_suppression_media(api, product, django_capture_on_commit_callbacks):
    used = product().images.get().media
    response = api.delete(f"{URL}/{used.pk}")
    assert response.status_code == 409 and response.json()["error"]["code"] == "media_in_use"
    free = MediaAsset.objects.get(pk=post(api, upload("libre.png", image_bytes(color=(9, 9, 9)))).json()["id"])
    path = free.file.path
    with django_capture_on_commit_callbacks(execute=True):
        assert api.delete(f"{URL}/{free.pk}").status_code == 204
    assert not MediaAsset.objects.filter(pk=free.pk).exists()
    import os

    assert not os.path.exists(path)


@pytest.mark.django_db
def test_nom_de_fichier_non_utilise_pour_le_stockage(api):
    post(api, upload("../../etc/passwd.png", image_bytes()))
    asset = MediaAsset.objects.get()
    assert ".." not in asset.file.name and asset.file.name.startswith("uploads/")
    assert asset.original_filename == "passwd.png"
