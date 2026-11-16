from django.conf import settings
from django.db import models


class Article(models.Model):
    """
    Article du blog (FR obligatoire, AR facultatif : vide = texte français affiché).
    Visible dans la boutique seulement s'il est « Publié » et que sa date de publication est passée.
    Le texte est du HTML limité (gras, titres, listes, liens), nettoyé par le serveur (apps.core.html).
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        PUBLISHED = "published", "Publié"

    title = models.CharField("titre", max_length=200)
    title_ar = models.CharField("titre (arabe)", max_length=200, blank=True)
    slug = models.SlugField("adresse", max_length=120, unique=True)
    excerpt = models.CharField("résumé", max_length=300, blank=True)
    excerpt_ar = models.CharField("résumé (arabe)", max_length=300, blank=True)
    body = models.TextField("texte", blank=True)
    body_ar = models.TextField("texte (arabe)", blank=True)
    cover = models.ForeignKey(
        "media_library.MediaAsset",
        verbose_name="image de couverture",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    cover_alt = models.CharField("texte alternatif de la couverture", max_length=255, blank=True)
    status = models.CharField("statut", max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    published_at = models.DateTimeField("date de publication", null=True, blank=True, db_index=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        verbose_name = "article"
        ordering = ["-published_at", "-id"]

    def __str__(self):
        return self.title
