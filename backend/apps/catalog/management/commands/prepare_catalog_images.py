"""
Prépare les images optimisées du catalogue (backend/catalog_import/images) à partir de catalogue.json.

    python manage.py prepare_catalog_images

- « copy_from » : image déjà optimisée dans src/assets, recopiée À L'IDENTIQUE (même empreinte → aucun doublon
  dans la médiathèque, rendu inchangé).
- « convert_from » et visuels marketing : l'original (backend/catalog_import/originaux, non versionné) est
  ré-encodé exactement comme un téléversement de l'administration : WebP qualité 85, 1600 px max + version 640 px,
  sans métadonnées, ratio conservé, jamais agrandi.
- Les originaux ne sont jamais modifiés. Le fichier images/INDEX.json garde poids avant/après et empreintes.
"""

import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.media_library.processing import process_upload

IMPORT_ROOT = Path(settings.BASE_DIR) / "catalog_import"
REPO_ROOT = Path(settings.BASE_DIR).parent


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inside(base: Path, relative: str) -> Path:
    path = (base / relative).resolve()
    if base.resolve() not in path.parents:
        raise CommandError(f"Chemin refusé : {relative}")
    return path


class Command(BaseCommand):
    help = "Produit les images optimisées des 6 produits à partir des originaux (sans les modifier)."

    def add_arguments(self, parser):
        parser.add_argument("--manifest", default=str(IMPORT_ROOT / "catalogue.json"))
        parser.add_argument("--originaux", default=str(IMPORT_ROOT / "originaux"))

    def handle(self, *args, **options):
        manifest = json.loads(Path(options["manifest"]).read_text(encoding="utf-8"))
        originals = Path(options["originaux"])
        index = {}
        for p in manifest["products"]:
            entries = [*p["gallery"], *([p["scene"]] if p.get("scene") else [])]
            for e in entries:
                index[e["file"]] = self._gallery(e, originals)
            for m in p["marketing"]:
                index[m["file"]] = self._convert(m["file"], m["original"], originals)
        out = IMPORT_ROOT / "images" / "INDEX.json"
        out.write_text(json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        before = sum(v.get("original_bytes") or 0 for v in index.values())
        after = sum(v["bytes"] + (v.get("bytes_640") or 0) for v in index.values())
        self.stdout.write(
            self.style.SUCCESS(f"{len(index)} images prêtes · originaux {before / 1e6:.1f} Mo → {after / 1e6:.2f} Mo")
        )

    def _write(self, relative: str, data: bytes) -> Path:
        path = inside(IMPORT_ROOT, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
        return path

    def _original_info(self, originals: Path, relative: str | None) -> dict:
        if not relative:
            return {"original": None, "original_bytes": None}
        path = inside(originals, relative)
        return {"original": relative, "original_bytes": path.stat().st_size if path.exists() else None}

    def _gallery(self, e: dict, originals: Path) -> dict:
        if e.get("convert_from"):
            return self._convert(e["file"], e["convert_from"], originals)
        source = inside(REPO_ROOT / "src" / "assets", e["copy_from"].removeprefix("src/assets/"))
        if not source.is_file():
            raise CommandError(f"Image introuvable : {e['copy_from']}")
        data = source.read_bytes()
        self._write(e["file"], data)
        info = {
            "mode": "copie",
            "key_sha256": sha256(data),
            "bytes": len(data),
            **self._original_info(originals, e.get("original")),
        }
        if e.get("file_640"):
            small = inside(REPO_ROOT / "src" / "assets", e["copy_from_640"].removeprefix("src/assets/")).read_bytes()
            self._write(e["file_640"], small)
            info.update(file_640=e["file_640"], bytes_640=len(small))
        return info

    def _convert(self, relative_out: str, relative_original: str, originals: Path) -> dict:
        source = inside(originals, relative_original)
        if not source.is_file():
            raise CommandError(f"Original introuvable : {relative_original} (dossier {originals})")
        data = source.read_bytes()
        processed = process_upload(data)
        self._write(relative_out, processed.main)
        info = {
            "mode": "conversion",
            # Même règle qu'un téléversement : l'empreinte est celle du fichier d'origine.
            "key_sha256": processed.sha256,
            "bytes": len(processed.main),
            "width": processed.width,
            "height": processed.height,
            "original": relative_original,
            "original_bytes": len(data),
        }
        if processed.small:
            small_path = relative_out.removesuffix(".webp") + "-640.webp"
            self._write(small_path, processed.small)
            info.update(file_640=small_path, bytes_640=len(processed.small))
        return info
