"""
Brouillon, publication et versions du thème.

Règles :
- le brouillon n'est JAMAIS visible des visiteurs ; la boutique lit la dernière version publiée ;
- enregistrer / publier exige la révision du brouillon que l'utilisateur a sous les yeux
  (409 « draft_conflict » sinon) : un brouillon modifié entre-temps n'est jamais publié par erreur ;
- publier crée une nouvelle version (ajout seul, dans une transaction) ; restaurer republie une copie
  d'une ancienne version (l'historique n'est jamais réécrit).
"""

import hashlib
import json

from django.db import transaction
from django.db.models import Max

from apps.audit.services import log_action
from apps.core.http import Conflict
from apps.media_library.models import MediaAsset

from .models import ThemeDraft, ThemeVersion
from .validation import default_theme, references, validate_theme


def checksum(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def latest_version() -> ThemeVersion | None:
    return ThemeVersion.objects.order_by("-number").first()


def get_draft(*, lock=False) -> ThemeDraft:
    """Le brouillon (créé au premier accès : copie de la version publiée, sinon thème par défaut)."""
    qs = ThemeDraft.objects.select_for_update() if lock else ThemeDraft.objects
    draft = qs.filter(pk=1).first()
    if draft is None:
        published = latest_version()
        ThemeDraft.objects.get_or_create(
            pk=1,
            defaults={"data": published.data if published else default_theme(), "based_on": published, "revision": 1},
        )
        draft = qs.get(pk=1)
    return draft


def _check_revision(draft: ThemeDraft, revision):
    if revision != draft.revision:
        who = draft.updated_by.email if draft.updated_by else "quelqu'un"
        raise Conflict(
            f"Le brouillon a été modifié entre-temps (par {who}). Rechargez-le avant de continuer.", "draft_conflict"
        )


@transaction.atomic
def save_draft(data, *, revision, user=None, request=None) -> ThemeDraft:
    value = validate_theme(data)
    draft = get_draft(lock=True)
    _check_revision(draft, revision)
    draft.data = value
    draft.revision += 1
    draft.updated_by = user
    draft.save()
    log_action(
        "theme.draft_save",
        actor=user,
        target_type="themes.themedraft",
        target_id=1,
        request=request,
        changes={"revision": draft.revision},
    )
    return draft


def _new_version(data, *, user, source, restored_from=None, note="") -> ThemeVersion:
    # Verrou sur le brouillon = sérialise les publications concurrentes (numéros sans trou ni doublon).
    number = (ThemeVersion.objects.aggregate(n=Max("number"))["n"] or 0) + 1
    return ThemeVersion.objects.create(
        number=number,
        data=data,
        checksum=checksum(data),
        source=source,
        restored_from=restored_from,
        note=note[:200],
        created_by=user,
    )


@transaction.atomic
def publish(*, revision, note="", user=None, request=None) -> ThemeVersion:
    draft = get_draft(lock=True)
    _check_revision(draft, revision)
    value = validate_theme(draft.data)  # revalidé : une image ou un produit a pu disparaître depuis
    current = latest_version()
    if current and current.checksum == checksum(value):
        raise Conflict("Ce brouillon est déjà la version publiée : rien à publier.", "nothing_to_publish")
    version = _new_version(value, user=user, source=ThemeVersion.Source.PUBLISH, note=note)
    draft.based_on = version
    draft.save(update_fields=["based_on", "updated_at"])
    log_action(
        "theme.publish",
        actor=user,
        target_type="themes.themeversion",
        target_id=version.pk,
        request=request,
        changes={"number": version.number, "draftRevision": draft.revision, "note": note[:200]},
    )
    return version


@transaction.atomic
def restore(version: ThemeVersion, *, user=None, request=None) -> ThemeVersion:
    """Republie une ancienne version (nouvelle version identique). Le brouillon n'est pas modifié."""
    get_draft(lock=True)
    value = validate_theme(version.data)
    current = latest_version()
    if current and current.pk == version.pk:
        raise Conflict("Cette version est déjà celle publiée.", "already_published")
    new = _new_version(
        value,
        user=user,
        source=ThemeVersion.Source.RESTORE,
        restored_from=version,
        note=f"Restauration de la version {version.number}",
    )
    log_action(
        "theme.restore",
        actor=user,
        target_type="themes.themeversion",
        target_id=new.pk,
        request=request,
        changes={"number": new.number, "restoredFrom": version.number},
    )
    return new


@transaction.atomic
def load_into_draft(version: ThemeVersion, *, revision, user=None, request=None) -> ThemeDraft:
    """Copie une version dans le brouillon (pour la retravailler). Rien n'est publié."""
    draft = get_draft(lock=True)
    _check_revision(draft, revision)
    draft.data = version.data
    draft.revision += 1
    draft.based_on = version
    draft.updated_by = user
    draft.save()
    log_action(
        "theme.draft_load",
        actor=user,
        target_type="themes.themedraft",
        target_id=1,
        request=request,
        changes={"version": version.number, "revision": draft.revision},
    )
    return draft


def media_payload(theme: dict) -> dict:
    """{id: {src, src640, width, height, alt}} pour les images du thème (URL publiques uniquement)."""
    ids = list(references(theme)["media"])
    out = {}
    for m in MediaAsset.objects.filter(pk__in=ids):
        out[str(m.pk)] = {
            "src": m.url,
            "src640": m.url_640 if m.file_640 else None,
            "width": m.width,
            "height": m.height,
            "alt": m.alt,
        }
    return out


def media_ids_in_use() -> set[int]:
    """Images utilisées par le brouillon ou par une version (restaurable) : elles ne doivent pas être supprimées."""
    ids: set[int] = set()
    draft = ThemeDraft.objects.filter(pk=1).first()
    datas = [draft.data] if draft else []
    datas += list(ThemeVersion.objects.values_list("data", flat=True))
    for data in datas:
        try:
            ids |= set(references(data)["media"])
        except (KeyError, TypeError, AttributeError):
            continue
    return ids


def is_dirty(draft: ThemeDraft) -> bool:
    """Le brouillon diffère-t-il de ce que voient les visiteurs (version publiée, sinon thème par défaut) ?"""
    current = latest_version()
    return checksum(draft.data) != (current.checksum if current else checksum(default_theme()))
