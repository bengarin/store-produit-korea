"""
Commandes (paiement à la livraison). Une commande n'est JAMAIS supprimée (PROTECT partout) :
on l'annule. Les lignes gardent une copie figée du produit, de la variante et du prix.
"""

from django.conf import settings
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente de confirmation"
        CONFIRMED = "confirmed", "Confirmée"
        SHIPPED = "shipped", "Expédiée"
        DELIVERED = "delivered", "Livrée"
        CANCELLED = "cancelled", "Annulée"
        RETURNED = "returned", "Retournée"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Non payée"
        PAID = "paid", "Payée (encaissée à la livraison)"
        REFUNDED = "refunded", "Remboursée"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "Paiement à la livraison"

    number = models.CharField("numéro", max_length=20, unique=True)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.COD)
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    # Livraison (copie figée au moment de la commande)
    ship_full_name = models.CharField("nom", max_length=120)
    ship_phone = models.CharField("téléphone", max_length=16)
    ship_city = models.ForeignKey("shipping.City", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    ship_city_label = models.CharField("ville", max_length=80)
    ship_address = models.CharField("adresse", max_length=255)
    shipping_zone_name = models.CharField(max_length=80, blank=True)
    # Montants recalculés par le serveur
    item_count = models.PositiveIntegerField(default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    coupon_code = models.CharField(max_length=40, blank=True)
    customer_note = models.CharField(max_length=500, blank=True)
    internal_note = models.TextField("note interne", blank=True)
    # Anti-doublon et traçabilité
    idempotency_key = models.CharField(max_length=64, unique=True)
    request_hash = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    placed_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "commande"
        ordering = ["-placed_at", "-id"]
        indexes = [
            models.Index(fields=["status", "placed_at"], name="order_status_date_idx"),
            models.Index(fields=["customer", "placed_at"], name="order_customer_date_idx"),
            models.Index(fields=["ship_phone", "placed_at"], name="order_phone_date_idx"),
            models.Index(fields=["placed_at"], name="order_date_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(subtotal__gte=0), name="order_subtotal_gte_0"),
            models.CheckConstraint(condition=models.Q(discount_total__gte=0), name="order_discount_gte_0"),
            models.CheckConstraint(condition=models.Q(shipping_fee__gte=0), name="order_shipping_gte_0"),
            models.CheckConstraint(condition=models.Q(total__gte=0), name="order_total_gte_0"),
            models.CheckConstraint(
                condition=models.Q(discount_total__lte=models.F("subtotal")), name="order_discount_lte_subtotal"
            ),
        ]

    def __str__(self):
        return self.number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="items")
    # PROTECT : une variante déjà commandée ne peut plus être supprimée (le catalogue l'archive).
    variant = models.ForeignKey("catalog.Variant", on_delete=models.PROTECT, related_name="order_items")
    product_slug = models.CharField(max_length=120)
    product_name = models.CharField(max_length=255)
    variant_title = models.CharField(max_length=160, blank=True)
    sku = models.CharField(max_length=64, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=1, quantity__lte=100), name="item_qty_range"),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="item_price_gte_0"),
            models.UniqueConstraint(fields=["order", "variant"], name="uniq_order_variant"),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="history")
    from_status = models.CharField(max_length=10, blank=True)
    to_status = models.CharField(max_length=10)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )  # None = client / système
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.order_id} {self.from_status or '∅'} → {self.to_status}"


class OrderNumberSequence(models.Model):
    """Compteur annuel des numéros de commande (incrémenté sous verrou)."""

    year = models.PositiveSmallIntegerField(primary_key=True)
    last_value = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.year}: {self.last_value}"
