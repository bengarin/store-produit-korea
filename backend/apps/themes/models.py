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
