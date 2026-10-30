"""
Commandes : devis (prix recalculés), création transactionnelle, changements de statut.

Règle d'or : le serveur ne fait JAMAIS confiance aux montants envoyés par le navigateur.
Il ne reçoit que des identifiants + quantités et recalcule tout depuis MySQL.
"""

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit.services import log_action
from apps.catalog.models import Product, Variant
from apps.core.http import Conflict
from apps.core.money import money, number
from apps.customers import services as customers
from apps.inventory.models import StockMovement
from apps.inventory.services import record_movement
from apps.promotions import services as promotions
from apps.promotions.models import CouponRedemption
from apps.shipping import services as shipping_svc
from apps.store_settings.models import StoreSettings

from .models import Order, OrderItem, OrderNumberSequence, OrderStatusHistory


# ============================== Devis ======================================
@dataclass
class Line:
    variant: Variant
    product: Product
    quantity: int

    @property
    def unit_price(self) -> Decimal:
        return self.variant.price

    @property
    def line_total(self) -> Decimal:
        return money(self.variant.price * self.quantity)


@dataclass
class Quote:
    lines: list[Line]
    subtotal: Decimal
    discount: Decimal = Decimal("0")
    shipping: Decimal = Decimal("0")
    coupon_result: promotions.CouponResult | None = None
    destination: shipping_svc.Destination | None = None
    stock_problems: list[dict] = field(default_factory=list)

    @property
    def item_count(self):
        return sum(line.quantity for line in self.lines)

    @property
    def total(self) -> Decimal:
        return money(self.subtotal - self.discount + self.shipping)

    def totals_payload(self):
        return {
            "itemCount": self.item_count,
            "subtotal": number(self.subtotal),
            "discount": number(self.discount),
            "delivery": number(self.shipping),
            "total": number(self.total),
        }


def resolve_lines(items: list[dict], *, lock=False) -> list[Line]:
    """
    items = [{"productId": slug, "variantId": int|None, "qty": int}]
    Produit ACTIF obligatoire ; sans variantId → variante par défaut. Les doublons sont regroupés.
    `lock=True` : verrouille les variantes (SELECT … FOR UPDATE) dans l'ordre des id (pas d'interblocage).
    """
    settings = StoreSettings.load()
    slugs = {i["productId"] for i in items}
    products = {p.slug: p for p in Product.objects.filter(slug__in=slugs, status=Product.Status.ACTIVE)}
    missing = sorted(slugs - set(products))
    if missing:
        raise ValidationError({"items": [f"Produit indisponible : {', '.join(missing)}."]}, code="unknown_product")

    wanted: dict[int, int] = {}
    for item in items:
        product = products[item["productId"]]
        variants = Variant.objects.filter(product=product)
        variant = (
            (variants.filter(pk=item["variantId"]) if item.get("variantId") else variants.filter(is_default=True))
            .values_list("pk", flat=True)
            .first()
        )
        if variant is None:
            raise ValidationError({"items": [f"Variante introuvable pour {product.public_name}."]})
        wanted[variant] = wanted.get(variant, 0) + item["qty"]

    qs = Variant.objects.select_related("product").filter(pk__in=wanted).order_by("pk")
    if lock:
        qs = qs.select_for_update()
    lines = []
    for variant in qs:
        qty = wanted[variant.pk]
        if qty > settings.max_qty_per_line:
            raise ValidationError({"items": [f"{settings.max_qty_per_line} articles maximum par produit."]})
        lines.append(Line(variant=variant, product=variant.product, quantity=qty))
    return lines


def stock_problems(lines: list[Line]) -> list[dict]:
    problems = []
    for line in lines:
        available = line.variant.available_quantity()  # None = illimité
        if available is not None and line.quantity > available:
            unknown = line.variant.stock_quantity is None
            problems.append(
                {
                    "productId": line.product.slug,
                    "variantId": line.variant.pk,
                    "name": line.product.public_name,
                    "requested": line.quantity,
                    "available": 0 if unknown else available,
                    "reason": "stock_unknown" if unknown else ("out_of_stock" if available == 0 else "insufficient"),
                }
            )
    return problems


def build_quote(items, *, promo_code=None, city=None, phone=None, lock=False) -> Quote:
    lines = resolve_lines(items, lock=lock)
    subtotal = money(sum((line.line_total for line in lines), Decimal("0")))
    quote = Quote(lines=lines, subtotal=subtotal, stock_problems=stock_problems(lines))
    if city is not None:
        quote.destination = shipping_svc.resolve_destination(city)
        quote.shipping = money(shipping_svc.shipping_fee(quote.destination.zone, subtotal))
    if promo_code:
        try:
            result = promotions.evaluate(promo_code, subtotal=subtotal, phone=phone, lock=lock)
        except promotions.CouponError as exc:
            raise ValidationError({"promoCode": [str(exc)]}, code="invalid_coupon") from exc
        quote.coupon_result = result
        quote.discount = result.discount
        if result.free_shipping:
            quote.shipping = Decimal("0")
    return quote


# ============================ Création =====================================
def request_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _next_number() -> str:
    year = timezone.localdate().year
    try:
        with transaction.atomic():
            OrderNumberSequence.objects.create(year=year, last_value=0)
    except IntegrityError:
        pass  # la ligne de l'année existe déjà
    seq = OrderNumberSequence.objects.select_for_update().get(year=year)
    seq.last_value = F("last_value") + 1
    seq.save(update_fields=["last_value"])
    seq.refresh_from_db()
    return f"MPC-{year}-{seq.last_value:06d}"


def order_response(order: Order) -> dict:
    """Réponse PUBLIQUE : aucune donnée personnelle (ni téléphone, ni adresse)."""
    return {
        "number": order.number,
        "createdAt": order.placed_at.isoformat(),
        "status": order.status,
        "totals": {
            "itemCount": order.item_count,
            "subtotal": number(order.subtotal),
            "discount": number(order.discount_total),
            "delivery": number(order.shipping_fee),
            "total": number(order.total),
        },
        "promoCode": order.coupon_code,
        "items": [
            {
                "productId": i.product_slug,
                "variantId": i.variant_id,
                "name": i.product_name,
                "variantTitle": i.variant_title,
                "price": number(i.unit_price),
                "qty": i.quantity,
                "lineTotal": number(i.line_total),
            }
            for i in order.items.all()
        ],
    }


class StockConflict(Conflict):
    def __init__(self, problems):
        super().__init__("Certains articles ne sont plus disponibles dans la quantité demandée.", "insufficient_stock")
        self.problems = problems


def create_order(data: dict, *, idempotency_key: str, request=None) -> tuple[Order, bool]:
    """
    Retourne (commande, créée). Une même clé d'idempotence renvoie la commande déjà créée
    (double clic, réseau coupé, nouvel essai) ; réutilisée pour un AUTRE contenu → 409.
    """
    fingerprint = request_hash(data)
    existing = Order.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return _replay(existing, fingerprint), False
    try:
        return _create(data, idempotency_key, fingerprint, request), True
    except IntegrityError:
        # Deux envois simultanés avec la même clé : le second retrouve la commande du premier.
        existing = Order.objects.filter(idempotency_key=idempotency_key).first()
        if existing is None:
            raise
        return _replay(existing, fingerprint), False


def _replay(order: Order, fingerprint: str) -> Order:
    if order.request_hash != fingerprint:
        raise Conflict("Cette clé de commande a déjà été utilisée pour une autre commande.", "idempotency_mismatch")
    return order


@transaction.atomic
def _create(data, idempotency_key, fingerprint, request) -> Order:
    customer_data = data["customer"]
    settings = StoreSettings.load()
    phone = customer_data["phone"]

    # Anti-abus : nombre de commandes par téléphone sur 1 heure (compté en base, donc exact).
    since = timezone.now() - timezone.timedelta(hours=1)
    if Order.objects.filter(ship_phone=phone, placed_at__gte=since).count() >= settings.max_orders_per_phone_per_hour:
        raise Conflict("Trop de commandes avec ce numéro. Réessayez plus tard ou contactez-nous.", "too_many_orders")

    quote = build_quote(
        data["items"], promo_code=data.get("promoCode"), city=customer_data["city"], phone=phone, lock=True
    )  # variantes et code promo verrouillés jusqu'à la fin de la transaction
    if quote.stock_problems:
        raise StockConflict(quote.stock_problems)

    customer = customers.get_or_create_customer(phone, customer_data["fullName"])
    destination = quote.destination
    order = Order.objects.create(
        number=_next_number(),
        customer=customer,
        ship_full_name=customer_data["fullName"],
        ship_phone=phone,
        ship_city=destination.city,
        ship_city_label=destination.label,
        ship_address=customer_data["address"],
        shipping_zone_name=destination.zone.name,
        item_count=quote.item_count,
        subtotal=quote.subtotal,
        discount_total=quote.discount,
        shipping_fee=quote.shipping,
        total=quote.total,
        coupon_code=quote.coupon_result.coupon.code if quote.coupon_result else "",
        customer_note=data.get("note", "")[:500],
        idempotency_key=idempotency_key,
        request_hash=fingerprint,
        ip_address=(request.META.get("REMOTE_ADDR") if request else None),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""),
    )
    for line in quote.lines:
        OrderItem.objects.create(
            order=order,
            variant=line.variant,
            product_slug=line.product.slug,
            product_name=line.product.public_name,
            variant_title=line.variant.title,
            sku=line.variant.sku or "",
            unit_price=line.unit_price,
            unit_cost=line.variant.cost,
            quantity=line.quantity,
            line_total=line.line_total,
        )
        if line.variant.track_inventory:
            record_movement(line.variant, -line.quantity, StockMovement.Reason.ORDER_PLACED, order=order)
    if quote.coupon_result:
        CouponRedemption.objects.create(
            coupon=quote.coupon_result.coupon, order=order, customer=customer, amount=quote.discount
        )
    OrderStatusHistory.objects.create(order=order, to_status=Order.Status.PENDING, note="Commande passée en ligne")
    customers.save_address(
        customer,
        full_name=order.ship_full_name,
        phone=phone,
        city=destination.city,
        city_label=destination.label,
        address_line=order.ship_address,
    )
    customers.refresh_stats(customer)
    log_action(
        "order.create",
        target=order,
        request=request,
        changes={"number": order.number, "total": str(order.total), "items": quote.item_count},
    )
    return order


# ============================ Statuts ======================================
TRANSITIONS = {
    Order.Status.PENDING: {Order.Status.CONFIRMED, Order.Status.CANCELLED},
    Order.Status.CONFIRMED: {Order.Status.SHIPPED, Order.Status.CANCELLED},
    Order.Status.SHIPPED: {Order.Status.DELIVERED, Order.Status.RETURNED},  # retour = refus à la livraison
    Order.Status.DELIVERED: {Order.Status.RETURNED},
    Order.Status.CANCELLED: set(),
    Order.Status.RETURNED: set(),
}
TIMESTAMPS = {
    "confirmed": "confirmed_at",
    "shipped": "shipped_at",
    "delivered": "delivered_at",
    "cancelled": "cancelled_at",
    "returned": "returned_at",
}


@transaction.atomic
def change_status(order: Order, to_status: str, *, user=None, note="", restock=True, request=None) -> Order:
    """
    Stock :
    - annulation (avant expédition) : TOUJOURS remis en stock (les articles ne sont pas partis) ;
    - retour : remis en stock si `restock` (par défaut oui ; non si les produits sont abîmés).
    Paiement à la livraison : « livrée » ⇒ payée ; « retournée » après livraison ⇒ remboursée.
    """
    order = Order.objects.select_for_update().get(pk=order.pk)
    current = order.status
    if to_status not in TRANSITIONS.get(current, set()):
        allowed = ", ".join(sorted(TRANSITIONS.get(current, set()))) or "aucun"
        raise Conflict(
            f"Passage de « {current} » à « {to_status} » impossible (possibles : {allowed}).", "invalid_transition"
        )

    restocked = False
    if to_status == Order.Status.CANCELLED or (to_status == Order.Status.RETURNED and restock):
        reason = (
            StockMovement.Reason.ORDER_CANCELLED
            if to_status == Order.Status.CANCELLED
            else StockMovement.Reason.ORDER_RETURNED
        )
        variant_ids = sorted(order.items.values_list("variant_id", flat=True))
        locked = {v.pk: v for v in Variant.objects.select_for_update().filter(pk__in=variant_ids).order_by("pk")}
        for item in order.items.order_by("variant_id"):
            variant = locked[item.variant_id]
            # On ne remet en stock que ce qui en était sorti (variantes suivies au moment de la commande).
            if order.stock_movements.filter(variant=variant, reason=StockMovement.Reason.ORDER_PLACED).exists():
                record_movement(variant, item.quantity, reason, order=order, user=user)
                restocked = True

    if to_status == Order.Status.CANCELLED:
        CouponRedemption.objects.filter(order=order, released_at__isnull=True).update(released_at=timezone.now())
    if to_status == Order.Status.DELIVERED:
        order.payment_status = Order.PaymentStatus.PAID
    if to_status == Order.Status.RETURNED and current == Order.Status.DELIVERED:
        order.payment_status = Order.PaymentStatus.REFUNDED

    order.status = to_status
    setattr(order, TIMESTAMPS[to_status], timezone.now())
    order.save()
    OrderStatusHistory.objects.create(
        order=order, from_status=current, to_status=to_status, changed_by=user, note=note[:500]
    )
    customers.refresh_stats(order.customer)
    log_action(
        "order.status",
        actor=user,
        target=order,
        request=request,
        changes={"status": [current, to_status], "restocked": restocked, "note": note},
    )
    return order
