from django.db import models


class ShippingZone(models.Model):
    """
    Zone de livraison avec son tarif. La zone `is_default` s'applique aux villes saisies librement
    (« Autre ville » du formulaire) ; sans zone par défaut, seules les villes listées sont acceptées.
    """

    name = models.CharField("nom", max_length=80, unique=True)
    fee = models.DecimalField("frais de livraison (DH)", max_digits=10, decimal_places=2)
    free_over_subtotal = models.DecimalField(
        "livraison offerte dès (DH)", max_digits=10, decimal_places=2, null=True, blank=True
    )
    delivery_days_min = models.PositiveSmallIntegerField("délai min. (jours)", null=True, blank=True)
    delivery_days_max = models.PositiveSmallIntegerField("délai max. (jours)", null=True, blank=True)
    is_default = models.BooleanField("zone par défaut (autres villes)", default=False)
    is_active = models.BooleanField("active", default=True)

    class Meta:
        verbose_name = "zone de livraison"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(condition=models.Q(fee__gte=0), name="zone_fee_gte_0"),
            models.CheckConstraint(
                condition=models.Q(free_over_subtotal__isnull=True) | models.Q(free_over_subtotal__gte=0),
                name="zone_free_over_gte_0",
            ),
        ]

    def __str__(self):
        return self.name


class City(models.Model):
    name = models.CharField("ville", max_length=80, unique=True)
    zone = models.ForeignKey(ShippingZone, on_delete=models.PROTECT, related_name="cities")
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField("proposée", default=True)

    class Meta:
        verbose_name = "ville"
        ordering = ["position", "name"]
        indexes = [models.Index(fields=["is_active", "position"], name="city_active_pos_idx")]

    def __str__(self):
        return self.name
