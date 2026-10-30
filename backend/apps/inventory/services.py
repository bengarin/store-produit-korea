"""
Toute modification de stock passe par ici et crée un mouvement (historique en ajout seul).
Les appelants doivent avoir VERROUILLÉ la variante (SELECT … FOR UPDATE) dans une transaction.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.audit.services import log_action
from apps.catalog.models import Variant

from .models import StockMovement


def record_movement(variant: Variant, delta: int, reason: str, *, order=None, user=None, note="") -> StockMovement:
    """Applique `delta` au stock (s'il est renseigné) et l'enregistre. Variante déjà verrouillée."""
    before = variant.stock_quantity
    after = None if before is None else before + delta
    if after is not None and after < 0 and not variant.allow_backorder:
        raise ValidationError({"quantity": ["Le stock ne peut pas devenir négatif."]})
    if after != before:
        variant.stock_quantity = after
        variant.save(update_fields=["stock_quantity", "updated_at"])
    return StockMovement.objects.create(
        variant=variant,
        delta=delta,
        quantity_before=before,
        quantity_after=after,
        reason=reason,
        order=order,
        user=user if getattr(user, "is_authenticated", False) else None,
        note=note[:255],
    )


@transaction.atomic
def adjust_stock(variant_id: int, *, mode: str, quantity: int, reason: str, note="", user=None, request=None):
    """
    Ajustement manuel :
    - mode "set"   : le stock devient `quantity` (comptage). Seul moyen de renseigner un stock inconnu.
    - mode "delta" : ajoute/retire `quantity` (ex. +12 réception, -1 produit abîmé). Stock déjà renseigné requis.
    """
    variant = Variant.objects.select_for_update().select_related("product").get(pk=variant_id)
    if reason not in StockMovement.MANUAL_REASONS:
        raise ValidationError({"reason": ["Motif non autorisé pour un ajustement manuel."]})
    before = variant.stock_quantity
    if mode == "set":
        if quantity < 0:
            raise ValidationError({"quantity": ["Le stock compté ne peut pas être négatif."]})
        delta = quantity - (before or 0)
        if before is not None and delta == 0:
            raise ValidationError({"quantity": ["Le stock est déjà à cette valeur."]})
        if before is None:
            reason = StockMovement.Reason.INITIAL_COUNT
        elif reason == StockMovement.Reason.INITIAL_COUNT:
            reason = StockMovement.Reason.RECOUNT
    elif mode == "delta":
        if before is None:
            raise ValidationError({"quantity": ["Stock non renseigné : faites d'abord un comptage (mode « set »)."]})
        if quantity == 0:
            raise ValidationError({"quantity": ["La variation ne peut pas être nulle."]})
        delta = quantity
    else:
        raise ValidationError({"mode": ["Mode inconnu (set ou delta)."]})

    if before is None:
        # Premier comptage : « non renseigné » → quantité réelle (quantity_before reste vide dans l'historique).
        variant.stock_quantity = quantity
        variant.save(update_fields=["stock_quantity", "updated_at"])
        movement = StockMovement.objects.create(
            variant=variant,
            delta=quantity,
            quantity_before=None,
            quantity_after=quantity,
            reason=reason,
            user=user if getattr(user, "is_authenticated", False) else None,
            note=note[:255],
        )
    else:
        movement = record_movement(variant, delta, reason, user=user, note=note)
    log_action(
        "inventory.adjust",
        actor=user,
        target=variant,
        request=request,
        changes={
            "product": variant.product.slug,
            "variant": variant.title,
            "before": before,
            "after": variant.stock_quantity,
            "reason": reason,
            "note": note,
        },
    )
    return movement
