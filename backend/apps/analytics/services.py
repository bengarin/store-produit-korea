"""
Rapport du tableau de bord, calculé sur les VRAIES commandes (MySQL). Aucune table propre, aucun cache.

DÉFINITIONS (reprises dans l'interface et dans docs/ARCHITECTURE.md) :
- Commande « valide » : ni annulée ni retournée (en attente, confirmée, expédiée, livrée).
- Montants : toujours les montants FIGÉS dans la commande (total, lignes) — jamais les prix actuels du catalogue.
- Chiffre d'affaires encaissé : total (livraison comprise, remise déduite) des commandes au statut « livrée »,
  compté à la DATE DE LIVRAISON (paiement à la livraison = encaissement ce jour-là). Une commande livrée puis
  retournée (remboursée) n'en fait plus partie.
- Tous les autres indicateurs de période sont comptés à la DATE DE COMMANDE (placed_at) :
  · commandes = toutes les commandes passées (tous statuts) ;
  · ventes commandées = total des commandes valides ; panier moyen = ventes commandées / commandes valides ;
  · unités vendues = quantités des lignes des commandes valides ;
  · clients = clients distincts ayant au moins une commande valide ; nouveaux clients = ceux dont la PREMIÈRE
    commande valide de toute l'histoire tombe dans la période ; clients existants = les autres ;
  · taux d'annulation = annulées / commandes passées ;
  · taux de retour = retournées / commandes parties chez le client (expédiées + livrées + retournées).
- Ventes par produit, variante, catégorie : montants des LIGNES (avant remise de commande, hors livraison)
  des commandes valides. Catégorie = catégorie principale ACTUELLE du produit (la commande ne la fige pas).
- Stock : état ACTUEL (pas de période). Stock 0 (« épuisé ») et stock non renseigné (NULL) sont toujours séparés.
- Jours, semaines (lundi → dimanche) et mois sont découpés à l'heure du Maroc.
"""

import datetime as dt
from collections import OrderedDict
from decimal import Decimal

from django.db.models import Count, F, Min, Q, Sum
from django.utils import timezone

from apps.catalog.models import Product, ProductCategory, Variant
from apps.core.money import money, number
from apps.customers.models import Customer
from apps.orders.models import Order, OrderItem

from .periods import Period

S = Order.Status
INVALID = (S.CANCELLED, S.RETURNED)
VALID = ~Q(status__in=INVALID)
LEFT_CUSTOMER = (S.SHIPPED, S.DELIVERED, S.RETURNED)  # commandes parties chez le client
GRANULARITIES = ("day", "week", "month")
TOP = 10
ZERO = Decimal("0")


def _ratio(numerator, denominator, scale=1):
    """Division sûre : None (« sans objet ») si le dénominateur est nul — jamais un 0 inventé."""
    if not denominator:
        return None
    return Decimal(numerator) * scale / Decimal(denominator)


def _pct(numerator, denominator):
    value = _ratio(numerator, denominator, 100)
    return None if value is None else float(value.quantize(Decimal("0.1")))


def _money(value):
    return None if value is None else number(money(value))


# --- Indicateurs ---------------------------------------------------------
def kpis(period: Period) -> dict:
    start, end = period.bounds()
    placed = Order.objects.filter(placed_at__gte=start, placed_at__lt=end)
    agg = placed.aggregate(
        orders=Count("id"),
        valid_orders=Count("id", filter=VALID),
        gross=Sum("total", filter=VALID),
        cancelled=Count("id", filter=Q(status=S.CANCELLED)),
        returned=Count("id", filter=Q(status=S.RETURNED)),
        left_customer=Count("id", filter=Q(status__in=LEFT_CUSTOMER)),
        customers=Count("customer", filter=VALID, distinct=True),
    )
    cashed = Order.objects.filter(status=S.DELIVERED, delivered_at__gte=start, delivered_at__lt=end).aggregate(
        revenue=Sum("total"), delivered=Count("id")
    )
    units = OrderItem.objects.filter(order__in=placed.filter(VALID)).aggregate(n=Sum("quantity"))["n"] or 0
    new_customers = (
        Order.objects.filter(VALID)
        .values("customer")
        .annotate(first=Min("placed_at"))
        .filter(first__gte=start, first__lt=end)
        .count()
    )
    gross = agg["gross"] or ZERO
    valid = agg["valid_orders"]
    customers = agg["customers"]
    return {
        "revenue": _money(cashed["revenue"] or ZERO),
        "deliveredOrders": cashed["delivered"],
        "orders": agg["orders"],
        "validOrders": valid,
        "grossSales": _money(gross),
        "averageOrderValue": _money(_ratio(gross, valid)),
        "unitsSold": units,
        "customers": customers,
        "newCustomers": new_customers,
        "returningCustomers": customers - new_customers,
        "ordersPerCustomer": None if not customers else float((_ratio(valid, customers)).quantize(Decimal("0.01"))),
        "valuePerCustomer": _money(_ratio(gross, customers)),
        "cancelled": agg["cancelled"],
        "returned": agg["returned"],
        "cancellationRate": _pct(agg["cancelled"], agg["orders"]),
        "returnRate": _pct(agg["returned"], agg["left_customer"]),
    }


RATE_KEYS = {"cancellationRate", "returnRate"}


def compare(current: dict, previous: dict) -> dict:
    """Évolution par indicateur : % pour les montants et volumes, points pour les taux. None si incalculable."""
    changes = {}
    for key, value in current.items():
        before = previous.get(key)
        if value is None or before is None:
            changes[key] = None
        elif key in RATE_KEYS:
            changes[key] = {"points": round(value - before, 1)}
        elif before == 0:
            changes[key] = None  # pas de % depuis zéro : on n'invente pas « +∞ % »
        else:
            changes[key] = {"percent": round((value - before) * 100 / before, 1)}
    return changes


# --- Séries temporelles --------------------------------------------------
def auto_granularity(period: Period) -> str:
    return "day" if period.days <= 31 else ("week" if period.days <= 120 else "month")


def _bucket(day: dt.date, granularity: str, period: Period) -> dt.date:
    if granularity == "day":
        return day
    first = day - dt.timedelta(days=day.weekday()) if granularity == "week" else day.replace(day=1)
    return max(first, period.start)  # 1re semaine / 1er mois éventuellement partiels


def series(period: Period, granularity: str) -> list[dict]:
    start, end = period.bounds()
    buckets = OrderedDict()
    day = period.start
    while day <= period.end:
        key = _bucket(day, granularity, period)
        if key not in buckets:
            buckets[key] = {"start": key, "end": key, "orders": 0, "grossSales": ZERO, "revenue": ZERO}
        buckets[key]["end"] = day
        day += dt.timedelta(days=1)
    # Regroupement à l'heure du Maroc en Python (indépendant des tables de fuseaux de MySQL) ;
    # les sommes par commande viennent des montants figés.
    for placed_at, total, status in Order.objects.filter(placed_at__gte=start, placed_at__lt=end).values_list(
        "placed_at", "total", "status"
    ):
        b = buckets[_bucket(timezone.localtime(placed_at).date(), granularity, period)]
        b["orders"] += 1
        if status not in INVALID:
            b["grossSales"] += total
    for delivered_at, total in Order.objects.filter(
        status=S.DELIVERED, delivered_at__gte=start, delivered_at__lt=end
    ).values_list("delivered_at", "total"):
        buckets[_bucket(timezone.localtime(delivered_at).date(), granularity, period)]["revenue"] += total
    return [
        {
            "start": b["start"].isoformat(),
            "end": b["end"].isoformat(),
            "orders": b["orders"],
            "grossSales": _money(b["grossSales"]),
            "revenue": _money(b["revenue"]),
        }
        for b in buckets.values()
    ]


# --- Répartitions --------------------------------------------------------
def breakdowns(period: Period) -> dict:
    start, end = period.bounds()
    placed = Order.objects.filter(placed_at__gte=start, placed_at__lt=end)
    labels = dict(S.choices)
    by_status = {s: n for s, n in placed.values_list("status").annotate(n=Count("id"))}
    statuses = [{"status": s, "label": labels[s], "orders": by_status.get(s, 0)} for s in S.values]

    pay_labels = dict(Order.PaymentMethod.choices)
    payments = [
        {
            "method": row["payment_method"],
            "label": pay_labels.get(row["payment_method"], row["payment_method"]),
            "orders": row["n"],
            "grossSales": _money(row["gross"]),
        }
        for row in placed.filter(VALID)
        .values("payment_method")
        .annotate(n=Count("id"), gross=Sum("total"))
        .order_by("-n")
    ]

    lines = OrderItem.objects.filter(order__in=placed.filter(VALID))
    per_product = {
        r["variant__product_id"]: r
        for r in lines.values("variant__product_id").annotate(units=Sum("quantity"), sales=Sum("line_total"))
    }
    primary = {}
    for link in (
        ProductCategory.objects.filter(product_id__in=per_product)
        .select_related("category")
        .order_by("product_id", "position", "id")
    ):
        primary.setdefault(link.product_id, link.category)
    categories = {}
    for product_id, r in per_product.items():
        cat = primary.get(product_id)
        key = cat.pk if cat else None
        entry = categories.setdefault(key, {"name": cat.name if cat else "Sans catégorie", "units": 0, "sales": ZERO})
        entry["units"] += r["units"]
        entry["sales"] += r["sales"]
    total_sales = sum((c["sales"] for c in categories.values()), ZERO)
    category_rows = sorted(categories.values(), key=lambda c: (-c["sales"], c["name"]))
    return {
        "statuses": statuses,
        "payments": payments,
        "categories": [
            {
                "name": c["name"],
                "units": c["units"],
                "sales": _money(c["sales"]),
                "share": _pct(c["sales"], total_sales),
            }
            for c in category_rows
        ],
    }


# --- Produits ------------------------------------------------------------
def _stock_row(v: Variant) -> dict:
    return {
        "variantId": v.pk,
        "productId": v.product_id,
        "productName": v.product.public_name,
        "productStatus": v.product.status,
        "variantTitle": v.title,
        "stockQuantity": v.stock_quantity,
        "lowStockThreshold": v.low_stock_threshold,
    }


def stock_state() -> dict:
    """État ACTUEL. Variantes suivies, sans vente à découvert, hors produits archivés."""
    tracked = (
        Variant.objects.filter(track_inventory=True, allow_backorder=False)
        .exclude(product__status=Product.Status.ARCHIVED)
        .select_related("product")
    )
    low = tracked.filter(stock_quantity__gt=0, stock_quantity__lte=F("low_stock_threshold")).order_by(
        "stock_quantity", "product__position", "position"
    )
    out = tracked.filter(stock_quantity__lte=0).order_by("product__position", "position")
    unknown = tracked.filter(stock_quantity__isnull=True).order_by("product__position", "position")
    return {
        "counts": {"low": low.count(), "outOfStock": out.count(), "unknown": unknown.count()},
        "low": [_stock_row(v) for v in low[:20]],
        "outOfStock": [_stock_row(v) for v in out[:20]],
        "unknown": [_stock_row(v) for v in unknown[:20]],
    }


def products(period: Period) -> dict:
    start, end = period.bounds()
    lines = OrderItem.objects.filter(order__placed_at__gte=start, order__placed_at__lt=end).exclude(
        order__status__in=INVALID
    )
    per_product = list(
        lines.values("variant__product_id").annotate(
            units=Sum("quantity"), sales=Sum("line_total"), orders=Count("order", distinct=True)
        )
    )
    names = {
        p.pk: (p.public_name, p.status)
        for p in Product.objects.filter(pk__in=[r["variant__product_id"] for r in per_product])
    }

    def product_row(r):
        name, status = names.get(r["variant__product_id"], ("", ""))
        return {
            "productId": r["variant__product_id"],
            "name": name,
            "status": status,
            "units": r["units"],
            "orders": r["orders"],
            "sales": _money(r["sales"]),
        }

    rows = [product_row(r) for r in per_product]
    by_units = sorted(rows, key=lambda r: (-r["units"], -r["sales"], r["name"]))[:TOP]
    by_sales = sorted(rows, key=lambda r: (-r["sales"], -r["units"], r["name"]))[:TOP]

    variants = []
    top_variants = list(
        lines.values("variant_id")
        .annotate(units=Sum("quantity"), sales=Sum("line_total"))
        .order_by("-units", "-sales", "variant_id")[:TOP]
    )
    found = Variant.objects.select_related("product").in_bulk([r["variant_id"] for r in top_variants])
    for r in top_variants:
        v = found[r["variant_id"]]
        variants.append(
            {
                "variantId": v.pk,
                "productId": v.product_id,
                "name": v.product.public_name,
                "variantTitle": v.title,
                "sku": v.sku or "",
                "units": r["units"],
                "sales": _money(r["sales"]),
            }
        )

    # Moins performants : produits ACTIFS, y compris ceux à 0 vente sur la période.
    sold = {r["productId"]: r for r in rows}
    least = sorted(
        (
            sold.get(p.pk)
            or {"productId": p.pk, "name": p.public_name, "status": p.status, "units": 0, "orders": 0, "sales": 0}
            for p in Product.objects.filter(status=Product.Status.ACTIVE)
        ),
        key=lambda r: (r["units"], r["sales"], r["name"]),
    )[:TOP]
    return {"topByUnits": by_units, "topBySales": by_sales, "topVariants": variants, "leastPerforming": least}


# --- Clients -------------------------------------------------------------
def customers(period: Period) -> dict:
    start, end = period.bounds()
    valid = Order.objects.filter(placed_at__gte=start, placed_at__lt=end).filter(VALID)
    top = list(
        valid.values("customer_id")
        .annotate(orders=Count("id"), spent=Sum("total"))
        .order_by("-orders", "-spent", "customer_id")[:TOP]
    )
    people = {c.pk: c for c in Customer.objects.filter(pk__in=[r["customer_id"] for r in top])}
    cities = list(
        valid.values("ship_city_label")
        .annotate(orders=Count("id"), gross=Sum("total"))
        .order_by("-orders", "-gross", "ship_city_label")
    )
    total_orders = sum(c["orders"] for c in cities)
    return {
        "top": [
            {
                "customerId": r["customer_id"],
                "name": people[r["customer_id"]].full_name,
                "anonymized": people[r["customer_id"]].anonymized_at is not None,
                "orders": r["orders"],
                "spent": _money(r["spent"]),
            }
            for r in top
        ],
        "cities": [
            {
                "city": c["ship_city_label"],
                "orders": c["orders"],
                "grossSales": _money(c["gross"]),
                "share": _pct(c["orders"], total_orders),
            }
            for c in cities
        ],
    }


def report(current: Period, previous: Period, granularity: str) -> dict:
    now_kpis, before_kpis = kpis(current), kpis(previous)
    stock = stock_state()
    return {
        "period": current.as_dict(),
        "previousPeriod": previous.as_dict(),
        "granularity": granularity,
        "kpis": now_kpis,
        "previousKpis": before_kpis,
        "changes": compare(now_kpis, before_kpis),
        "series": series(current, granularity),
        **breakdowns(current),
        "products": products(current),
        "customers": customers(current),
        "stock": stock,
        # Hors période : ce qui attend une action maintenant
        "toProcess": Order.objects.filter(status=S.PENDING).count(),
        "recentOrders": [
            {
                "id": o.pk,
                "number": o.number,
                "customerName": o.ship_full_name,
                "city": o.ship_city_label,
                "status": o.status,
                "total": number(o.total),
                "placedAt": o.placed_at.isoformat(),
            }
            for o in Order.objects.order_by("-placed_at", "-id")[:8]
        ],
    }
