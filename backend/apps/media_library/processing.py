"""
Validation et traitement SÉCURISÉ des images téléversées.

Règles :
- taille ≤ MEDIA_MAX_UPLOAD_BYTES ; formats acceptés : JPEG, PNG, WebP (vérifiés par le CONTENU,
  jamais par l'extension ou le type annoncé) ; SVG, GIF, HTML déguisés… refusés ;
- dimensions entre 200 px et MEDIA_MAX_SIDE px ; protection contre les « bombes » de décompression ;
- l'image est ré-encodée en WebP : métadonnées (EXIF, GPS) et contenu caché supprimés ;
- une version 640 px est créée pour les petits écrans.
"""

import hashlib
import io
import warnings
from dataclasses import dataclass

from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MIN_SIDE = 200


class ImageRejected(ValueError):
    """Image refusée : le message est affiché tel quel à l'utilisateur."""


@dataclass
class ProcessedImage:
    main: bytes
    small: bytes | None
    width: int
    height: int
    sha256: str  # empreinte du fichier d'ORIGINE (détecte les doublons)


def _limits():
    return (
        settings.MEDIA_MAX_UPLOAD_BYTES,
        settings.MEDIA_MAX_SIDE,
        settings.MEDIA_STORED_MAX_SIDE,
    )


def _open_checked(data: bytes, max_side: int) -> Image.Image:
    # Bombe de décompression : au-delà de cette surface, Pillow lève une erreur au lieu de décoder.
    Image.MAX_IMAGE_PIXELS = max_side * max_side
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            probe = Image.open(io.BytesIO(data))
            fmt = probe.format
            probe.verify()  # détecte un fichier tronqué ou corrompu
            image = Image.open(io.BytesIO(data))
            image.load()
        except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise ImageRejected("Fichier non reconnu comme image valide (JPEG, PNG ou WebP).") from exc
        except (OSError, SyntaxError, ValueError) as exc:
            raise ImageRejected("Image corrompue ou illisible.") from exc
    if fmt not in ALLOWED_FORMATS:
        raise ImageRejected("Format non accepté. Formats autorisés : JPEG, PNG, WebP.")
    width, height = image.size
    if width > max_side or height > max_side:
        raise ImageRejected(f"Image trop grande (maximum {max_side} × {max_side} px).")
    if width < MIN_SIDE or height < MIN_SIDE:
        raise ImageRejected(f"Image trop petite (minimum {MIN_SIDE} × {MIN_SIDE} px).")
    return image


def _to_webp(image: Image.Image, max_side: int) -> tuple[bytes, int, int]:
    img = image.copy()
    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="WEBP", quality=85, method=6)  # aucune métadonnée recopiée
    return buffer.getvalue(), img.width, img.height


def process_upload(data: bytes) -> ProcessedImage:
    max_bytes, max_side, stored_side = _limits()
    if len(data) > max_bytes:
        raise ImageRejected(f"Fichier trop lourd (maximum {max_bytes // (1024 * 1024)} Mo).")
    if not data:
        raise ImageRejected("Fichier vide.")
    image = _open_checked(data, max_side)
    image = ImageOps.exif_transpose(image)  # applique la rotation de l'appareil photo, puis on jette l'EXIF
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "A" in image.getbands() or image.mode == "P" else "RGB")
    main, width, height = _to_webp(image, stored_side)
    small = _to_webp(image, 640)[0] if max(image.size) > 640 else None
    return ProcessedImage(main=main, small=small, width=width, height=height, sha256=hashlib.sha256(data).hexdigest())


def inspect_existing(data: bytes) -> tuple[int, int, str]:
    """Pour l'import des images du dépôt : vérifie l'image SANS la modifier (rendu identique)."""
    _max_bytes, max_side, _ = _limits()
    image = _open_checked(data, max_side)
    return image.width, image.height, Image.MIME.get(image.format, "image/webp")
