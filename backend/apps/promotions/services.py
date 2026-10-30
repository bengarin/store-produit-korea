from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from apps.core.money import money

from .models import Coupon, CouponRedemption


class CouponError(Exception):
    """Code refusé : le message est affiché tel quel au client."""


@dataclass
class CouponResult:
    coupon: Coupon
    discount: Decimal
    free_shipping: bool


def evaluate(code: str, *, subtotal: Decimal, phone: str | None = None, lock=False) -> CouponResult:
    """Vérifie un code et calcule la remise. `lock=True` (dans une transaction) verrouille le code."""
    qs = Coupon.objects.select_for_update() if lock else Coupon.objects
    coupon = qs.filter(code=(code or "").strip().upper()).first()
    now = timezone.now()
    if coupon is None or not coupon.is_active:
        raise CouponError("Ce code promo n'est pas valide.")
    if (coupon.starts_at and now < coupon.starts_at) or (coupon.ends_at and now > coupon.ends_at):
        raise CouponError("Ce code promo n'est pas valable actuellement.")
    if coupon.min_subtotal is not None and subtotal < coupon.min_subtotal:
        raise CouponError(f"Ce code est valable à partir de {coupon.min_subtotal:.0f} DH d'achat.")
    active = CouponRedemption.objects.filter(coupon=coupon, released_at__isnull=True)
    if coupon.usage_limit is not None and active.count() >= coupon.usage_limit:
        raise CouponError("Ce code promo a atteint son nombre maximal d'utilisations.")
    per_customer = coupon.usage_limit_per_customer
    if phone and per_customer is not None and active.filter(customer__phone=phone).count() >= per_customer:
        raise CouponError("Vous avez déjà utilisé ce code promo.")

    if coupon.type == Coupon.Type.PERCENTAGE:
        discount = money(subtotal * coupon.value / Decimal(100))
    elif coupon.type == Coupon.Type.FIXED_AMOUNT:
        discount = min(money(coupon.value), subtotal)
    else:
        discount = Decimal("0")
    return CouponResult(coupon=coupon, discount=discount, free_shipping=coupon.type == Coupon.Type.FREE_SHIPPING)


def public_payload(result: CouponResult) -> dict:
    """Ce que le front peut savoir d'un code VALIDE (jamais la liste des codes)."""
    from apps.core.money import number

    return {
        "code": result.coupon.code,
        "type": result.coupon.type,
        "value": number(result.coupon.value),
        "minSubtotal": number(result.coupon.min_subtotal),
        "discount": number(result.discount),
    }
