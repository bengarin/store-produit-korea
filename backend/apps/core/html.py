"""Assainissement du HTML saisi dans l'administration (description longue)."""

import nh3

ALLOWED_TAGS = {"p", "br", "h2", "h3", "strong", "em", "u", "ul", "ol", "li", "a", "blockquote"}
ALLOWED_ATTRIBUTES = {"a": {"href", "title"}}


def sanitize_html(value: str) -> str:
    """Retire scripts, styles, attributs d'événements et liens dangereux (javascript:, data:…)."""
    if not value:
        return ""
    return nh3.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"https", "http", "mailto"},
        link_rel="noopener noreferrer nofollow",
    ).strip()
