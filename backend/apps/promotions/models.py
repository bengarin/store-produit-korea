from django.db import models


class Coupon(models.Model):
    class Type(models.TextChoices):
        PERCENTAGE = "percentage", "Pourcentage"
        FIXED_AMOUNT = "fixed_amount", "Montant fixe (DH)"
        FREE_SHIPPING = "free_shipping", "Livraison offerte"

    code = models.CharField("code", max_length=40, unique=True)  # toujours en MAJUSCULES
    type = models.CharField(max_length=20, choices=Type.choices)
    value = models.DecimalField("valeur", max_digits=10, decimal_places=2, default=0)
    min_subtotal = models.DecimalField(
        "sous-total minimum (DH)", max_digits=10, decimal_places=2, null=True, blank=True
    )
    starts_at = models.DateTimeField("début", null=True, blank=True)
    ends_at = models.DateTimeField("fin", null=True, blank=True)
    usage_limit = models.PositiveIntegerField("utilisations max. (total)", null=True, blank=True)
    usage_limit_per_customer = models.PositiveIntegerField("utilisations max. par client", null=True, blank=True)
    is_active = models.BooleanField("actif", default=True)
    note = models.CharField("note interne", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "code promo"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(value__gte=0), name="coupon_value_gte_0"),
            models.CheckConstraint(
                condition=~models.Q(type="percentage") | models.Q(value__gt=0, value__lte=100),
                name="coupon_percentage_range",
            ),
            models.CheckConstraint(
                condition=~models.Q(type="fixed_amount") | models.Q(value__gt=0), name="coupon_fixed_gt_0"
            ),
        ]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        super().save(*args, **kwargs)


class CouponRedemption(models.Model):
    """Utilisation d'un code par une commande. Libérée (released_at) si la commande est annulée."""

    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, related_name="redemptions")
    order = models.OneToOneField("orders.Order", on_delete=models.PROTECT, related_name="coupon_redemption")
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="coupon_redemptions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["coupon", "released_at"], name="redemption_active_idx")]

    def __str__(self):
        return f"{self.coupon} → {self.order_id}"
