"""
Statistiques du tableau de bord, calculées sur les VRAIES commandes (MySQL). Aucune table propre.

Définitions (affichées dans l'interface) :
- orders          : commandes passées sur la période (tous statuts)
- grossSales      : valeur des commandes passées, hors annulées et retournées
- revenue         : chiffre d'affaires ENCAISSÉ = total des commandes livrées (paiement à la livraison)
- averageOrderValue : grossSales / nombre de commandes hors annulées et retournées
La période porte sur la date de commande (placed_at), en heure du Maroc.
"""

import datetime as dt
from collections import OrderedDict
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from apps.catalog.models import Variant
from apps.core.money import money, number
from apps.orders.models import Order

VALID = ~Q(status__in=[Order.Status.CANCELLED, Order.Status.RETURNED])
MAX_DAYS = 366


def period_bounds(date_from: dt.date, date_to: dt.date):
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(dt.datetime.combine(date_from, dt.time.min), tz)
    end = timezone.make_aware(dt.datetime.combine(date_to + dt.timedelta(days=1), dt.time.min), tz)
    return start, end


def overview(date_from: dt.date, date_to: dt.date) -> dict:
    start, end = period_bounds(date_from, date_to)
    orders = Order.objects.filter(placed_at__gte=start, placed_at__lt=end)

    agg = orders.aggregate(
        orders=Count("id"),
        valid_orders=Count("id", filter=VALID),
        gross=Sum("total", filter=VALID),
        revenue=Sum("total", filter=Q(status=Order.Status.DELIVERED)),
    )
    by_status = dict(orders.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    gross = agg["gross"] or Decimal("0")
    valid = agg["valid_orders"] or 0

    # Ventilation par jour (heure du Maroc), faite en Python : indépendante des tables de fuseaux MySQL.
    days = OrderedDict()
    day = date_from
    while day <= date_to:
        days[day] = {"date": day.isoformat(), "orders": 0, "grossSales": Decimal("0"), "revenue": Decimal("0")}
        day += dt.timedelta(days=1)
    for placed_at, total, status in orders.values_list("placed_at", "total", "status"):
        bucket = days[timezone.localtime(placed_at).date()]
        bucket["orders"] += 1
        if status not in (Order.Status.CANCELLED, Order.Status.RETURNED):
            bucket["grossSales"] += total
        if status == Order.Status.DELIVERED:
            bucket["revenue"] += total
    series = [{**d, "grossSales": number(d["grossSales"]), "revenue": number(d["revenue"])} for d in days.values()]

    tracked = Variant.objects.filter(track_inventory=True, allow_backorder=False).exclude(product__status="archived")
    stock = {
        "unknown": tracked.filter(stock_quantity__isnull=True).count(),
        "outOfStock": tracked.filter(stock_quantity__lte=0).count(),
        "low": tracked.filter(stock_quantity__gt=0, stock_quantity__lte=F("low_stock_threshold")).count(),
    }
    alerts = (
        tracked.filter(Q(stock_quantity__isnull=True) | Q(stock_quantity__lte=F("low_stock_threshold")))
        .select_related("product")
        .order_by(F("stock_quantity").asc(nulls_first=True), "product__position")[:8]
    )

    return {
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "kpis": {
            "orders": agg["orders"],
            "grossSales": number(money(gross)),
            "revenue": number(money(agg["revenue"] or 0)),
            "averageOrderValue": number(money(gross / valid)) if valid else 0,
            "pending": by_status.get(Order.Status.PENDING, 0),
            "confirmed": by_status.get(Order.Status.CONFIRMED, 0),
            "shipped": by_status.get(Order.Status.SHIPPED, 0),
            "delivered": by_status.get(Order.Status.DELIVERED, 0),
            "cancelled": by_status.get(Order.Status.CANCELLED, 0),
            "returned": by_status.get(Order.Status.RETURNED, 0),
        },
        # Hors période : ce qui attend une action maintenant
        "toProcess": Order.objects.filter(status=Order.Status.PENDING).count(),
        "series": series,
        "stock": stock,
        "stockAlerts": [
            {
                "variantId": v.pk,
                "productName": v.product.public_name,
                "variantTitle": v.title,
                "stockQuantity": v.stock_quantity,
                "lowStockThreshold": v.low_stock_threshold,
            }
            for v in alerts
        ],
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
