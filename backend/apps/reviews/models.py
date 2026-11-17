from django.conf import settings
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


class ProductReview(models.Model):
    """
    Avis d'un client sur UN PRODUIT (distinct des avis sur la boutique ci-dessus et des témoignages du thème).
    Déposé depuis la fiche produit (statut « En attente ») ou saisi par l'équipe à partir d'un vrai message
    client (origine obligatoire). Publié seulement après approbation.
    « Achat vérifié » : uniquement si l'avis est relié à une commande LIVRÉE contenant ce produit.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        APPROVED = "approved", "Approuvé"
        REJECTED = "rejected", "Refusé"

    class Source(models.TextChoices):
        CUSTOMER = "customer", "Formulaire de la fiche produit"
        ADMIN = "admin", "Saisi par l'équipe (avis client reçu)"

    product = models.ForeignKey(
        "catalog.Product", verbose_name="produit", on_delete=models.CASCADE, related_name="reviews"
    )
    name = models.CharField("nom affiché", max_length=60)
    rating = models.PositiveSmallIntegerField("note", validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField("avis", max_length=1000)
    language = models.CharField("langue", max_length=2, choices=[("fr", "Français"), ("ar", "Arabe")], default="fr")
    status = models.CharField("statut", max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    source = models.CharField("origine", max_length=10, choices=Source.choices, default=Source.CUSTOMER)
    # Saisie par l'équipe : d'où vient l'avis (ex. « Message WhatsApp du 12/11 ») — preuve qu'il est authentique.
    source_note = models.CharField("provenance de l'avis", max_length=200, blank=True)
    consent_text = models.CharField("texte de consentement accepté", max_length=240, blank=True)
    order = models.ForeignKey(
        "orders.Order",
        verbose_name="commande liée",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="product_reviews",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("déposé le", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)
    moderated_at = models.DateTimeField("modéré le", null=True, blank=True)
    approved_at = models.DateTimeField("approuvé le", null=True, blank=True)

    class Meta:
        verbose_name = "avis produit"
        verbose_name_plural = "avis produits"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["product", "status"], name="product_review_status_idx")]
        constraints = [
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name="product_review_rating_1_5"),
        ]

    def __str__(self):
        return f"{self.product_id} · {self.name} ({self.rating}/5)"

    @property
    def verified_purchase(self) -> bool:
        """Vrai seulement si la commande liée est livrée ET contient ce produit."""
        if not self.order_id:
            return False
        order = self.order
        if order.status != order.Status.DELIVERED:
            return False
        return order.items.filter(variant__product_id=self.product_id).exists()
