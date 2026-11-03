import re
from dataclasses import dataclass
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from apps.store_settings.models import StoreSettings

from .models import City, ShippingZone

# Ville saisie à la main : lettres latines (accents compris) ou arabes, espaces, apostrophe, tiret.
FREE_CITY = re.compile(r"^[A-Za-zÀ-ÿ\u0600-\u06FF' \-]{2,80}$")


@dataclass
class Destination:
    city: City | None
    label: str
    zone: ShippingZone | None


def resolve_destination(label: str) -> Destination:
    label = " ".join((label or "").split())
    city = City.objects.select_related("zone").filter(name__iexact=label, is_active=True, zone__is_active=True).first()
    if city:
        return Destination(city=city, label=city.name, zone=city.zone)
    if not FREE_CITY.match(label):
        raise ValidationError({"city": ["Nom de ville invalide."]})
    default = ShippingZone.objects.filter(is_default=True, is_active=True).first()
    if default is not None:  # comportement par défaut : tarif de la zone « autres villes »
        return Destination(city=None, label=label, zone=default)
    if StoreSettings.load().delivery_mode != StoreSettings.DeliveryMode.ZONES:
        # Livraison gratuite ou montant unique : les frais ne dépendent d'aucune zone.
        return Destination(city=None, label=label, zone=None)
    raise ValidationError({"city": ["Ville non desservie ou invalide."]})


def delivery_rule(zone: ShippingZone | None) -> tuple[Decimal | None, Decimal | None]:
    """
    (frais, seuil de gratuité) selon la configuration de livraison de l'administration :
    gratuite → 0 ; payante → montant unique configuré ; par zone → tarif et seuil de la zone.
    Seule source de vérité : utilisée pour la commande (serveur) et pour l'affichage (/store/config).
    """
    settings = StoreSettings.load()
    if settings.delivery_mode == StoreSettings.DeliveryMode.FREE:
        return Decimal("0"), None
    if settings.delivery_mode == StoreSettings.DeliveryMode.PAID:
        return settings.delivery_fee, None
    if zone is None:
        return None, None
    return zone.fee, zone.free_over_subtotal


def shipping_fee(zone: ShippingZone | None, subtotal: Decimal) -> Decimal:
    """Frais facturés, toujours calculés ici (jamais repris du navigateur)."""
    fee, free_over = delivery_rule(zone)
    if free_over is not None and subtotal >= free_over:
        return Decimal("0")
    return fee
