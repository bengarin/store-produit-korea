"""
Thème de la boutique (boutique unique) : UN brouillon modifiable + des versions publiées en ajout seul.

- ThemeDraft (ligne unique, pk=1) : ce que l'équipe modifie ; `revision` augmente à chaque enregistrement
  et protège contre l'écrasement du travail d'un collègue (409 si la révision envoyée n'est pas la dernière).
- ThemeVersion : chaque publication crée une version (numéro croissant) ; jamais modifiée ni supprimée.
  La boutique publique affiche TOUJOURS la version de plus grand numéro. Restaurer = republier une copie.
"""

from django.conf import settings
from django.db import models


class ThemeDraft(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    data = models.JSONField()
    revision = models.PositiveIntegerField(default=1)
    based_on = models.ForeignKey("ThemeVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "brouillon du thème"
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="theme_draft_singleton")]

    def __str__(self):
        return f"Brouillon (révision {self.revision})"


class ThemeVersion(models.Model):
    class Source(models.TextChoices):
        PUBLISH = "publish", "Publication du brouillon"
        RESTORE = "restore", "Restauration d'une version"

    number = models.PositiveIntegerField("numéro", unique=True)
    data = models.JSONField()
    checksum = models.CharField(max_length=64)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.PUBLISH)
    restored_from = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    note = models.CharField("note", max_length=200, blank=True)
    created_at = models.DateTimeField("publiée le", auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "version publiée du thème"
        ordering = ["-number"]

    def __str__(self):
        return f"Version {self.number}"


class HeroSlide(models.Model):
    """
    Diapositive de la bannière principale de l'accueil (Admin → Visuels marketing → Bannière d'accueil).
    1 diapositive publiée = bannière fixe ; plusieurs = carrousel. Les textes restent du TEXTE (FR/AR) posé
    sur l'image, jamais incrusté dedans. Image : un média de la médiathèque OU un visuel intégré au site
    (`*_asset`, ex. la bannière d'origine). Arabe vide = la boutique arabe utilise la traduction du texte français.
    """

    BUILTIN_DESKTOP = ("hero-wide", "hero-portrait")
    BUILTIN_MOBILE = ("hero-portrait", "hero-wide")

    position = models.PositiveIntegerField("ordre", default=0, db_index=True)
    is_active = models.BooleanField("publiée", default=True)
    desktop_media = models.ForeignKey(
        "media_library.MediaAsset", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    desktop_asset = models.CharField("visuel intégré (ordinateur)", max_length=40, blank=True)
    mobile_media = models.ForeignKey(
        "media_library.MediaAsset", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    mobile_asset = models.CharField("visuel intégré (mobile)", max_length=40, blank=True)
    eyebrow_fr = models.CharField("sur-titre (FR)", max_length=80, blank=True)
    eyebrow_ar = models.CharField("sur-titre (AR)", max_length=80, blank=True)
    title_fr = models.CharField("titre (FR)", max_length=120)
    title_ar = models.CharField("titre (AR)", max_length=120, blank=True)
    text_fr = models.CharField("description (FR)", max_length=300, blank=True)
    text_ar = models.CharField("description (AR)", max_length=300, blank=True)
    button_label_fr = models.CharField("texte du bouton (FR)", max_length=40, blank=True)
    button_label_ar = models.CharField("texte du bouton (AR)", max_length=40, blank=True)
    button_link = models.CharField("lien du bouton", max_length=300, blank=True)
    alt_fr = models.CharField("texte alternatif (FR)", max_length=255, blank=True)
    alt_ar = models.CharField("texte alternatif (AR)", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "diapositive de la bannière d'accueil"
        ordering = ["position", "id"]

    def __str__(self):
        return self.title_fr
