"""
Validation d'un thème côté serveur (l'autorité). Mêmes règles que src/theme/validate.js, à partir du MÊME
fichier : shared/theme/schema.json. Aucun HTML, CSS ni script : uniquement des textes (sans < ni >),
des couleurs #rrggbb, des choix dans des listes fermées, des liens contrôlés et des références vérifiées
en base (images de la médiathèque, produits, catégories).

validate_theme(data) → données normalisées, ou ValidationError {"chemin.du.champ": ["message"]}.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from rest_framework.exceptions import ValidationError

AREAS = ("announcement", "header", "footer")
TOP_KEYS = {"schemaVersion", "settings", "announcement", "header", "home", "footer"}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,119}$")
HTML_RE = re.compile(r"[<>]")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
LINK_RES = {
    "internal": re.compile(r"^/(?!/)[A-Za-z0-9\-._~/?=&%+]*$"),
    "anchor": re.compile(r"^#[a-z][a-z0-9-]{0,39}$"),
    "external": re.compile(r"^https://[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+(/[A-Za-z0-9\-._~/?=&%+#]*)?$"),
}


def shared_dir() -> Path:
    return Path(getattr(settings, "THEME_SHARED_DIR", settings.BASE_DIR.parent / "shared" / "theme"))


@lru_cache(maxsize=1)
def schema() -> dict:
    return json.loads((shared_dir() / "schema.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _default_theme_text() -> str:
    return (shared_dir() / "default-theme.json").read_text(encoding="utf-8")


def default_theme() -> dict:
    return json.loads(_default_theme_text())  # copie neuve à chaque appel


def check_field(field: dict, raw):
    """(valeur normalisée, message d'erreur ou None) — même logique que checkField (JS)."""
    value = field.get("default") if raw is None else raw  # absent ou null = valeur par défaut
    kind = field["type"]
    if kind in ("text", "textarea"):
        if not isinstance(value, str):
            return value, "Texte attendu."
        v = " ".join(value.split()) if kind == "text" else value.replace("\r\n", "\n").replace("\r", "\n").strip()
        if HTML_RE.search(v):
            return v, "Les caractères < et > (balises HTML) ne sont pas autorisés."
        if CONTROL_RE.search(v):
            return v, "Caractères invisibles non autorisés."
        if field.get("maxLength") and len(v) > field["maxLength"]:
            return v, f"{field['maxLength']} caractères maximum."
        if field.get("required") and not v:
            return v, "Champ obligatoire."
        return v, None
    if kind == "color":
        if not isinstance(value, str) or not COLOR_RE.match(value):
            return value, "Couleur attendue au format #RRGGBB."
        return value.lower(), None
    if kind == "select":
        return (value, None) if any(o["value"] == value for o in field["options"]) else (value, "Choix non autorisé.")
    if kind == "font":
        return (
            (value, None) if isinstance(value, str) and value in schema()["fonts"] else (value, "Police non autorisée.")
        )
    if kind == "icon":
        return (value, None) if value in schema()["icons"] else (value, "Icône non autorisée.")
    if kind == "link":
        if not isinstance(value, str):
            return value, "Lien invalide."
        v = value.strip()
        if not v:
            return v, ("Champ obligatoire." if field.get("required") else None)
        kinds = field.get("kinds") or ["internal", "anchor", "external"]
        if len(v) > 300 or not any(LINK_RES[k].match(v) for k in kinds):
            if len(kinds) == 1:
                return v, "Lien interne attendu (ex. /produits)."
            return v, "Lien interne (/produits), ancre (#collection) ou adresse https:// uniquement."
        return v, None
    if kind == "image":
        if value in (None, ""):
            return None, ("Image obligatoire." if field.get("required") else None)
        if not isinstance(value, dict) or len(value) != 1:
            return value, "Image invalide."
        if "asset" in value:
            ok = value["asset"] in (field.get("assets") or [])
            return ({"asset": value["asset"]}, None) if ok else (value, "Image non autorisée.")
        media_id = value.get("mediaId")
        if isinstance(media_id, int) and not isinstance(media_id, bool) and media_id > 0:
            return {"mediaId": media_id}, None
        return value, "Image invalide."
    if kind in ("product", "category"):
        if not isinstance(value, str):
            return value, "Référence invalide."
        if not value:
            return "", ("Champ obligatoire." if field.get("required") else None)
        return (value, None) if SLUG_RE.match(value) else (value, "Référence invalide.")
    return value, "Type de champ inconnu."


def _fields(fields, raw, path, errors):
    out = {}
    if not isinstance(raw, dict):
        errors[path] = ["Objet attendu."]
        return out
    known = {f["id"] for f in fields}
    for key in raw:
        if key not in known:
            errors[f"{path}.{key}"] = ["Réglage inconnu."]
    for f in fields:
        value, err = check_field(f, raw.get(f["id"]))
        out[f["id"]] = value
        if err:
            errors[f"{path}.{f['id']}"] = [err]
    return out


def _section(raw, path, errors, ids, area):
    if not isinstance(raw, dict):
        errors[path] = ["Section invalide."]
        return None
    definition = schema()["sections"].get(raw.get("type")) if isinstance(raw.get("type"), str) else None
    if not definition or definition["area"] != area:
        errors[f"{path}.type"] = ["Type de section non autorisé ici."]
        return None
    allowed = {"id", "type", "disabled", "settings"} | ({"items"} if definition.get("items") else set())
    for key in raw:
        if key not in allowed:
            errors[f"{path}.{key}"] = ["Clé inconnue."]
    section_id = raw.get("id")
    if not isinstance(section_id, str) or not re.match(schema()["limits"]["idPattern"], section_id):
        errors[f"{path}.id"] = ["Identifiant invalide."]
    elif section_id in ids:
        errors[f"{path}.id"] = ["Identifiant en double."]
    else:
        ids.add(section_id)
    disabled = raw.get("disabled", False)
    if not isinstance(disabled, bool):
        errors[f"{path}.disabled"] = ["Vrai ou faux attendu."]
    section = {
        "id": section_id,
        "type": raw["type"],
        "disabled": bool(disabled),
        "settings": _fields(
            definition["settings"],
            raw.get("settings") if raw.get("settings") is not None else {},
            f"{path}.settings",
            errors,
        ),
    }
    items_def = definition.get("items")
    if items_def:
        items = raw.get("items") if raw.get("items") is not None else []
        if not isinstance(items, list):
            errors[f"{path}.items"] = ["Liste attendue."]
        else:
            if len(items) < items_def["min"]:
                errors[f"{path}.items"] = [f"{items_def['min']} élément(s) minimum."]
            if len(items) > items_def["max"]:
                errors[f"{path}.items"] = [f"{items_def['max']} éléments maximum."]
            section["items"] = [
                _fields(items_def["settings"], it, f"{path}.items.{i}", errors)
                for i, it in enumerate(items[: items_def["max"]])
            ]
    return section


def validate_structure(data):
    """Règles du schéma (sans base de données). Retourne (valeur normalisée, erreurs {chemin: [message]})."""
    errors: dict[str, list[str]] = {}
    sch = schema()
    if not isinstance(data, dict):
        return None, {"": ["Thème invalide."]}
    for key in data:
        if key not in TOP_KEYS:
            errors[key] = ["Clé inconnue."]
    if data.get("schemaVersion") != sch["schemaVersion"]:
        errors["schemaVersion"] = ["Version de schéma non prise en charge."]
    ids: set[str] = set()
    value = {
        "schemaVersion": sch["schemaVersion"],
        "settings": _fields(
            sch["settings"], data.get("settings") if data.get("settings") is not None else {}, "settings", errors
        ),
    }
    for area in AREAS:
        value[area] = _section(data.get(area), area, errors, ids, area)
    home = data.get("home")
    if not isinstance(home, list):
        errors["home"] = ["Liste de sections attendue."]
        value["home"] = []
    else:
        if len(home) > sch["limits"]["maxHomeSections"]:
            errors["home"] = [f"{sch['limits']['maxHomeSections']} sections maximum."]
        counts: dict[str, int] = {}
        sections = []
        for i, raw in enumerate(home):
            section = _section(raw, f"home.{i}", errors, ids, "home")
            if section:
                counts[section["type"]] = counts.get(section["type"], 0) + 1
                definition = sch["sections"][section["type"]]
                if definition.get("max") and counts[section["type"]] > definition["max"]:
                    errors[f"home.{i}.type"] = [f"{definition['max']} section(s) « {definition['name']} » maximum."]
                sections.append(section)
        value["home"] = sections
    return value, errors


def references(theme: dict) -> dict:
    """Références à vérifier en base : {"media": {id: [chemins]}, "product": {...}, "category": {...}}."""
    found = {"media": {}, "product": {}, "category": {}}
    sections = schema()["sections"]

    def scan(fields, values, path):
        for f in fields:
            v = values.get(f["id"])
            if f["type"] == "image" and isinstance(v, dict) and "mediaId" in v:
                found["media"].setdefault(v["mediaId"], []).append(f"{path}.{f['id']}")
            elif f["type"] in ("product", "category") and v:
                found[f["type"]].setdefault(v, []).append(f"{path}.{f['id']}")

    all_sections = [(a, theme.get(a)) for a in AREAS] + [
        (f"home.{i}", s) for i, s in enumerate(theme.get("home") or [])
    ]
    for path, section in all_sections:
        if not section:
            continue
        definition = sections[section["type"]]
        scan(definition["settings"], section["settings"], f"{path}.settings")
        for i, item in enumerate(section.get("items") or []):
            scan(definition["items"]["settings"], item, f"{path}.items.{i}")
    return found


def validate_theme(data) -> dict:
    """Validation complète (schéma + taille + références en base). Lève ValidationError."""
    from apps.catalog.models import Category, Product
    from apps.media_library.models import MediaAsset

    try:
        size = len(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise ValidationError({"": ["Thème illisible."]}) from exc
    if size > schema()["limits"]["maxBytes"]:
        raise ValidationError({"": ["Thème trop volumineux."]})
    value, errors = validate_structure(data)
    if not errors:
        refs = references(value)
        checks = (
            (
                "media",
                MediaAsset.objects.filter(pk__in=refs["media"]).values_list("pk", flat=True),
                "Image introuvable dans la médiathèque.",
            ),
            (
                "product",
                Product.objects.filter(slug__in=refs["product"]).values_list("slug", flat=True),
                "Produit introuvable.",
            ),
            (
                "category",
                Category.objects.filter(slug__in=refs["category"]).values_list("slug", flat=True),
                "Catégorie introuvable.",
            ),
        )
        for kind, existing, message in checks:
            missing = set(refs[kind]) - set(existing)
            for ref in missing:
                for path in refs[kind][ref]:
                    errors[path] = [message]
    if errors:
        raise ValidationError(errors)
    return value
