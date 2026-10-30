import re
from dataclasses import dataclass
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from .models import City, ShippingZone

FREE_CITY = re.compile(r"^[A-Za-zÀ-ÿ' \-]{2,80}$")


@dataclass
class Destination:
    city: City | None
    label: str
    zone: ShippingZone


def resolve_destination(label: str) -> Destination:
    label = " ".join((label or "").split())
    city = City.objects.select_related("zone").filter(name__iexact=label, is_active=True, zone__is_active=True).first()
    if city:
        return Destination(city=city, label=city.name, zone=city.zone)
    default = ShippingZone.objects.filter(is_default=True, is_active=True).first()
    if default is None or not FREE_CITY.match(label):
        raise ValidationError({"city": ["Ville non desservie ou invalide."]})
    return Destination(city=None, label=label, zone=default)


def shipping_fee(zone: ShippingZone, subtotal: Decimal) -> Decimal:
    if zone.free_over_subtotal is not None and subtotal >= zone.free_over_subtotal:
        return Decimal("0")
    return zone.fee
