"""Bannière d'accueil (diapositives) : données publiques et création de la 1re diapositive depuis le thème."""

from .models import HeroSlide

# Traductions arabes déjà validées des textes de la bannière d'origine (src/i18n/content.js).
ORIGINAL_AR = {
    "La beauté au naturel": "الجمال بطبيعته",
    "Des soins doux pour une peau plus belle chaque jour": "عناية لطيفة لبشرة أجمل كل يوم",
    "Une sélection de soins naturels pour une peau saine, lumineuse et harmonieuse.": (
        "تشكيلة من منتجات العناية الطبيعية لبشرة صحية ومشرقة ومتوازنة."
    ),
    "Découvrir nos produits": "اكتشفوا منتجاتنا",
    (
        "Les cinq soins de la boutique sur des socles en pierre : gel Baroness Aloe Vera, crème SOME BY MI Yuja "
        "Niacin, émulsion ORJENA Power Collagen, patchs BIOVÈNE et crème Quret Vitamin Collagen"
    ): (
        "منتجات العناية الخمسة على قواعد حجرية: جل Baroness Aloe Vera، وكريم SOME BY MI Yuja Niacin، "
        "ومستحلب ORJENA Power Collagen، ولصقات BIOVÈNE، وكريم Quret Vitamin Collagen"
    ),
}


def image_value(media_id, asset):
    if media_id:
        return {"mediaId": media_id}
    if asset:
        return {"asset": asset}
    return None


def slide_payload(s: HeroSlide) -> dict:
    return {
        "id": s.pk,
        "imageDesktop": image_value(s.desktop_media_id, s.desktop_asset),
        "imageMobile": image_value(s.mobile_media_id, s.mobile_asset),
        "eyebrow": {"fr": s.eyebrow_fr, "ar": s.eyebrow_ar},
        "title": {"fr": s.title_fr, "ar": s.title_ar},
        "text": {"fr": s.text_fr, "ar": s.text_ar},
        "buttonLabel": {"fr": s.button_label_fr, "ar": s.button_label_ar},
        "buttonLink": s.button_link,
        "alt": {"fr": s.alt_fr, "ar": s.alt_ar},
    }


def public_slides():
    return list(HeroSlide.objects.filter(is_active=True).order_by("position", "id"))


def hero_payload(media_payload_fn) -> dict:
    """{slides: [...], media: {...}} — diapositives PUBLIÉES uniquement, dans l'ordre."""
    slides = public_slides()
    ids = {i for s in slides for i in (s.desktop_media_id, s.mobile_media_id) if i}
    return {"slides": [slide_payload(s) for s in slides], "media": media_payload_fn(ids)}


def slide_from_theme_settings(settings: dict) -> dict:
    """Champs d'une diapositive à partir des réglages de la section « hero » d'un thème (bannière actuelle)."""

    def text(key, limit):
        value = settings.get(key) or ""
        return value[:limit] if isinstance(value, str) else ""

    def image(key):
        value = settings.get(key) or {}
        if not isinstance(value, dict):
            return None, ""
        if isinstance(value.get("mediaId"), int):
            return value["mediaId"], ""
        return None, value.get("asset") or ""

    desktop_id, desktop_asset = image("imageDesktop")
    mobile_id, mobile_asset = image("imageMobile")
    fields = {
        "eyebrow_fr": text("eyebrow", 80),
        "title_fr": text("heading", 120) or "Jodhur",
        "text_fr": text("text", 300),
        "button_label_fr": text("buttonLabel", 40),
        "button_link": text("buttonLink", 300),
        "alt_fr": text("imageAlt", 255),
        "desktop_media_id": desktop_id,
        "desktop_asset": desktop_asset,
        "mobile_media_id": mobile_id,
        "mobile_asset": mobile_asset,
    }
    for key in ("eyebrow", "title", "text", "button_label", "alt"):
        fields[f"{key}_ar"] = ORIGINAL_AR.get(fields[f"{key}_fr"], "")
    return fields
