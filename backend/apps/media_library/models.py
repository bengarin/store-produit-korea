from django.conf import settings
from django.db import models


class MediaAsset(models.Model):
    """
    Fichier image stocké (local en développement, stockage externe plus tard via STORAGES).
    Les fichiers téléversés sont TOUJOURS ré-encodés en WebP (voir processing.py).
    Suppression : refusée tant qu'un produit l'utilise (FK PROTECT côté catalogue).
    """

    class Source(models.TextChoices):
        UPLOAD = "upload", "Téléversement"
        IMPORT = "import", "Import du catalogue de démonstration"

    file = models.FileField("fichier", upload_to="", max_length=255)
    file_640 = models.FileField("version 640 px", upload_to="", max_length=255, blank=True)
    original_filename = models.CharField("nom d'origine", max_length=255, blank=True)
    mime_type = models.CharField("type", max_length=50)
    width = models.PositiveIntegerField("largeur")
    height = models.PositiveIntegerField("hauteur")
    size_bytes = models.PositiveIntegerField("taille (octets)")
    sha256 = models.CharField("empreinte SHA-256", max_length=64, unique=True)
    alt = models.CharField("texte alternatif", max_length=255, blank=True)
    source = models.CharField("origine", max_length=10, choices=Source.choices, default=Source.UPLOAD)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("ajouté le", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "média"
        verbose_name_plural = "médias"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(width__gt=0, height__gt=0), name="media_dimensions_positive"),
        ]

    def __str__(self):
        return self.original_filename or self.file.name

    @property
    def url(self):
        return self.file.url if self.file else ""

    @property
    def url_640(self):
        return self.file_640.url if self.file_640 else ""
