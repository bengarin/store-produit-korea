from django.conf import settings
from django.db import models


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise PermissionError("L'historique du stock est en ajout seul.")

    def delete(self):
        raise PermissionError("L'historique du stock est en ajout seul.")


class StockMovement(models.Model):
    """
    Chaque changement de stock d'une variante, sans exception (ajout seul).
    `quantity_before` = None si le stock n'était pas encore renseigné.
    """

    class Reason(models.TextChoices):
        INITIAL_COUNT = "initial_count", "Premier comptage"
        RECOUNT = "recount", "Inventaire (recomptage)"
        RESTOCK = "restock", "Réapprovisionnement"
        MANUAL_ADJUSTMENT = "manual_adjustment", "Ajustement manuel"
        DAMAGED = "damaged", "Produit abîmé / perdu"
        ORDER_PLACED = "order_placed", "Commande passée"
        ORDER_CANCELLED = "order_cancelled", "Commande annulée (remise en stock)"
        ORDER_RETURNED = "order_returned", "Commande retournée (remise en stock)"

    MANUAL_REASONS = frozenset({"initial_count", "recount", "restock", "manual_adjustment", "damaged"})

    variant = models.ForeignKey("catalog.Variant", on_delete=models.PROTECT, related_name="stock_movements")
    delta = models.IntegerField("variation")
    quantity_before = models.IntegerField("stock avant", null=True, blank=True)
    quantity_after = models.IntegerField("stock après", null=True, blank=True)
    reason = models.CharField("motif", max_length=20, choices=Reason.choices)
    note = models.CharField("note", max_length=255, blank=True)
    order = models.ForeignKey(
        "orders.Order", null=True, blank=True, on_delete=models.PROTECT, related_name="stock_movements"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        verbose_name = "mouvement de stock"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["variant", "created_at"], name="stockmove_variant_idx"),
            models.Index(fields=["reason", "created_at"], name="stockmove_reason_idx"),
        ]

    def __str__(self):
        return f"{self.variant_id} {self.delta:+d} ({self.reason})"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionError("Un mouvement de stock ne peut pas être modifié.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Un mouvement de stock ne peut pas être supprimé.")
