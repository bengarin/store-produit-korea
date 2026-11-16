from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class StoreReview(models.Model):
    """
    Avis d'un client sur la BOUTIQUE (pas sur un produit). Déposé depuis la page « Avis » ; il n'apparaît
    qu'après validation par l'équipe (statut « Approuvé »). Seuls le prénom (ou pseudo), la note, le texte et la
    date sont publiés : aucune adresse e-mail ni téléphone n'est demandée.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        APPROVED = "approved", "Approuvé"

    name = models.CharField("nom affiché", max_length=60)
    rating = models.PositiveSmallIntegerField("note", validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField("avis", max_length=1000)
    language = models.CharField("langue", max_length=2, choices=[("fr", "Français"), ("ar", "Arabe")], default="fr")
    status = models.CharField("statut", max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    consent_text = models.CharField("texte de consentement accepté", max_length=240)
    created_at = models.DateTimeField("déposé le", auto_now_add=True, db_index=True)
    approved_at = models.DateTimeField("approuvé le", null=True, blank=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        verbose_name = "avis sur la boutique"
        verbose_name_plural = "avis sur la boutique"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name="store_review_rating_1_5"),
        ]

    def __str__(self):
        return f"{self.name} ({self.rating}/5)"
