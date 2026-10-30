"""Téléphones marocains — même règle que le front (src/utils/phone.js)."""

import re

_PATTERN = re.compile(r"^(?:\+212|00212|212|0)([5-7]\d{8})$")


def normalize_moroccan_phone(value: str | None) -> str | None:
    """'06 12 34 56 78' → '+212612345678' (E.164) ; None si invalide."""
    cleaned = re.sub(r"[\s.\-()]", "", value or "")
    match = _PATTERN.match(cleaned)
    return f"+212{match.group(1)}" if match else None
