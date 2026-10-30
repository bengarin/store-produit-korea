from django.db import models


class StoreSettings(models.Model):
    """Réglages uniques de la boutique (une seule ligne, id = 1)."""

    # Clé fixe (pas d'auto-incrément) : MySQL peut alors garantir une seule ligne via la contrainte.
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    brand_name = models.CharField("nom de la boutique", max_length=100, default="Ma Petite Corée")
    whatsapp_number = models.CharField("numéro WhatsApp (international, chiffres seuls)", max_length=20, blank=True)
    contact_email = models.EmailField("e-mail de contact", blank=True)
    contact_phone = models.CharField("téléphone de contact", max_length=20, blank=True)
    # Mentions légales des factures — [À VÉRIFIER avec un comptable]
    legal_name = models.CharField("raison sociale", max_length=150, blank=True)
    legal_address = models.TextField("adresse", blank=True)
    ice = models.CharField("ICE", max_length=20, blank=True)
    rc = models.CharField("RC", max_length=30, blank=True)
    if_number = models.CharField("IF", max_length=30, blank=True)
    invoice_footer = models.CharField("pied de facture", max_length=255, blank=True)
    max_qty_per_line = models.PositiveSmallIntegerField("quantité max. par produit", default=20)
    max_orders_per_phone_per_hour = models.PositiveSmallIntegerField(
        "commandes max. par téléphone et par heure", default=5
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "réglages de la boutique"
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="store_settings_singleton")]

    def __str__(self):
        return self.brand_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "StoreSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
