"""
La bannière d'accueil ACTUELLE devient la diapositive n° 1 (publiée) : mêmes textes, mêmes images, même lien.
Lue dans la dernière version publiée du thème (sinon le thème par défaut du site). Ajout seul : rien d'autre
n'est modifié ; ne fait rien si une diapositive existe déjà.
"""

from django.db import migrations


def seed(apps, schema_editor):
    from apps.themes.hero import slide_from_theme_settings
    from apps.themes.validation import default_theme

    HeroSlide = apps.get_model("themes", "HeroSlide")
    ThemeVersion = apps.get_model("themes", "ThemeVersion")
    MediaAsset = apps.get_model("media_library", "MediaAsset")
    if HeroSlide.objects.exists():
        return
    current = ThemeVersion.objects.order_by("-number").first()
    data = current.data if current else default_theme()
    hero = next((s for s in data.get("home", []) if s.get("type") == "hero"), None)
    if hero is None:
        hero = next(s for s in default_theme()["home"] if s["type"] == "hero")
    fields = slide_from_theme_settings(hero.get("settings") or {})
    # Image de la médiathèque supprimée entre-temps : on retombe sur le visuel d'origine.
    for side, fallback in (("desktop", "hero-wide"), ("mobile", "hero-portrait")):
        media_id = fields[f"{side}_media_id"]
        if media_id and not MediaAsset.objects.filter(pk=media_id).exists():
            fields[f"{side}_media_id"] = None
            fields[f"{side}_asset"] = fallback
    if not fields["desktop_media_id"] and not fields["desktop_asset"]:
        fields["desktop_asset"] = "hero-wide"
    HeroSlide.objects.create(position=0, is_active=not hero.get("disabled", False), **fields)


class Migration(migrations.Migration):
    dependencies = [("themes", "0002_hero_slides"), ("media_library", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
