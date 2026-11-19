from rest_framework import serializers

from apps.media_library.models import MediaAsset

from .models import HeroSlide
from .validation import check_field

TEXT_FIELDS = {
    "eyebrow_fr": 80,
    "eyebrow_ar": 80,
    "title_fr": 120,
    "title_ar": 120,
    "text_fr": 300,
    "text_ar": 300,
    "button_label_fr": 40,
    "button_label_ar": 40,
    "alt_fr": 255,
    "alt_ar": 255,
}


def _media(m: MediaAsset | None):
    if m is None:
        return None
    return {"id": m.pk, "url": m.url, "url640": m.url_640 or None, "width": m.width, "height": m.height}


class HeroSlideSerializer(serializers.ModelSerializer):
    """Diapositive (administration). Mettre une image de la médiathèque remplace le visuel intégré."""

    desktopMediaId = serializers.PrimaryKeyRelatedField(
        source="desktop_media", queryset=MediaAsset.objects.all(), required=False, allow_null=True
    )
    mobileMediaId = serializers.PrimaryKeyRelatedField(
        source="mobile_media", queryset=MediaAsset.objects.all(), required=False, allow_null=True
    )
    desktopAsset = serializers.CharField(source="desktop_asset", required=False, allow_blank=True)
    mobileAsset = serializers.CharField(source="mobile_asset", required=False, allow_blank=True)
    desktop = serializers.SerializerMethodField()
    mobile = serializers.SerializerMethodField()
    eyebrowFr = serializers.CharField(source="eyebrow_fr", required=False, allow_blank=True)
    eyebrowAr = serializers.CharField(source="eyebrow_ar", required=False, allow_blank=True)
    titleFr = serializers.CharField(source="title_fr", required=False, allow_blank=True)
    titleAr = serializers.CharField(source="title_ar", required=False, allow_blank=True)
    textFr = serializers.CharField(source="text_fr", required=False, allow_blank=True)
    textAr = serializers.CharField(source="text_ar", required=False, allow_blank=True)
    buttonLabelFr = serializers.CharField(source="button_label_fr", required=False, allow_blank=True)
    buttonLabelAr = serializers.CharField(source="button_label_ar", required=False, allow_blank=True)
    buttonLink = serializers.CharField(source="button_link", required=False, allow_blank=True)
    altFr = serializers.CharField(source="alt_fr", required=False, allow_blank=True)
    altAr = serializers.CharField(source="alt_ar", required=False, allow_blank=True)
    isActive = serializers.BooleanField(source="is_active", required=False)

    class Meta:
        model = HeroSlide
        fields = [
            "id",
            "position",
            "isActive",
            "desktopMediaId",
            "desktopAsset",
            "desktop",
            "mobileMediaId",
            "mobileAsset",
            "mobile",
            "eyebrowFr",
            "eyebrowAr",
            "titleFr",
            "titleAr",
            "textFr",
            "textAr",
            "buttonLabelFr",
            "buttonLabelAr",
            "buttonLink",
            "altFr",
            "altAr",
        ]
        read_only_fields = ["position"]

    def get_desktop(self, obj):
        return _media(obj.desktop_media)

    def get_mobile(self, obj):
        return _media(obj.mobile_media)

    def validate(self, attrs):
        errors = {}
        camel = {f.source: name for name, f in self.fields.items() if getattr(f, "source", None)}
        for key, limit in TEXT_FIELDS.items():
            if key in attrs:
                kind = "textarea" if key.startswith("text_") else "text"
                value, error = check_field({"type": kind, "maxLength": limit}, attrs[key])
                attrs[key] = value
                if error:
                    errors[camel[key]] = [error]
        if "button_link" in attrs:
            value, error = check_field({"type": "link"}, attrs["button_link"])
            attrs["button_link"] = value
            if error:
                errors["buttonLink"] = [error]
        if attrs.get("desktop_media"):
            attrs["desktop_asset"] = ""
        if attrs.get("mobile_media"):
            attrs["mobile_asset"] = ""
        for key, allowed in (("desktop_asset", HeroSlide.BUILTIN_DESKTOP), ("mobile_asset", HeroSlide.BUILTIN_MOBILE)):
            if attrs.get(key) and attrs[key] not in allowed:
                errors[camel[key]] = ["Visuel non autorisé."]

        def current(key):
            return attrs[key] if key in attrs else getattr(self.instance, key, None)

        if not (current("title_fr") or "").strip():
            errors["titleFr"] = ["Le titre en français est obligatoire."]
        if not current("desktop_media") and not current("desktop_asset"):
            errors["desktopMediaId"] = ["L'image pour ordinateur est obligatoire."]
        has_label = (current("button_label_fr") or "").strip() or (current("button_label_ar") or "").strip()
        if has_label and not (current("button_link") or "").strip():
            errors["buttonLink"] = ["Indiquez la destination du bouton (ex. /produits)."]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
