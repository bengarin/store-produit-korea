import hashlib
import uuid
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.audit.services import log_action
from apps.core.http import Conflict

from .models import MediaAsset
from .processing import inspect_existing, process_upload


def _clean_name(name: str) -> str:
    return Path(name or "").name[:255]


def create_from_upload(uploaded_file, *, alt="", user=None, request=None) -> tuple[MediaAsset, bool]:
    """Valide, ré-encode et enregistre. Retourne (média, créé). Un doublon renvoie le média existant."""
    data = uploaded_file.read()
    processed = process_upload(data)  # lève ImageRejected si refusé
    existing = MediaAsset.objects.filter(sha256=processed.sha256).first()
    if existing:
        return existing, False

    stem = f"uploads/{timezone.now():%Y/%m}/{uuid.uuid4().hex}"
    asset = MediaAsset(
        original_filename=_clean_name(uploaded_file.name),
        mime_type="image/webp",
        width=processed.width,
        height=processed.height,
        size_bytes=len(processed.main),
        sha256=processed.sha256,
        alt=alt[:255],
        uploaded_by=user if getattr(user, "is_authenticated", False) else None,
    )
    asset.file.save(f"{stem}.webp", ContentFile(processed.main), save=False)
    if processed.small:
        asset.file_640.save(f"{stem}-640.webp", ContentFile(processed.small), save=False)
    try:
        with transaction.atomic():
            asset.save()
    except IntegrityError:  # envoi simultané du même fichier
        _delete_files(asset)
        return MediaAsset.objects.get(sha256=processed.sha256), False
    log_action(
        "media.upload",
        actor=user,
        target=asset,
        changes={"filename": asset.original_filename, "width": asset.width, "height": asset.height},
        request=request,
    )
    return asset, True


def create_from_repository_file(path: Path, *, alt="", path_640: Path | None = None, folder="imports") -> MediaAsset:
    """
    Import d'une image DÉJÀ présente dans le dépôt (catalogue de démonstration) : le fichier est vérifié
    mais copié à l'identique pour que la boutique s'affiche exactement comme avant.
    """
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    existing = MediaAsset.objects.filter(sha256=digest).first()
    if existing:
        return existing
    width, height, mime = inspect_existing(data)
    asset = MediaAsset(
        original_filename=path.name,
        mime_type=mime,
        width=width,
        height=height,
        size_bytes=len(data),
        sha256=digest,
        alt=alt[:255],
        source=MediaAsset.Source.IMPORT,
    )
    asset.file.save(f"{folder}/{path.name}", ContentFile(data), save=False)
    if path_640 is not None:
        inspect_existing(path_640.read_bytes())
        asset.file_640.save(f"{folder}/{path_640.name}", ContentFile(path_640.read_bytes()), save=False)
    asset.save()
    return asset


def _delete_files(asset):
    for field in (asset.file, asset.file_640):
        if field:
            field.storage.delete(field.name)


def delete_asset(asset: MediaAsset, *, user=None, request=None):
    try:
        with transaction.atomic():
            snapshot = {"filename": asset.original_filename, "file": asset.file.name}
            asset_id = asset.pk
            asset.delete()
            log_action(
                "media.delete",
                actor=user,
                target_type="media_library.mediaasset",
                target_id=asset_id,
                changes=snapshot,
                request=request,
            )
    except ProtectedError as exc:
        raise Conflict("Ce média est utilisé par un produit : retirez-le d'abord du produit.", "media_in_use") from exc
    transaction.on_commit(lambda: _delete_files(asset))
