"""
Importe la configuration actuelle du front (src/config/store.js) : nom, WhatsApp, villes,
frais de livraison et code promo de démonstration.

    python manage.py import_store_config            # crée ce qui manque, ne modifie rien d'existant
    python manage.py import_store_config --update   # ré-aligne sur le fichier

Comportement reproduit à l'identique : une zone « Maroc » au tarif du front, qui accepte aussi
« Autre ville » (zone par défaut), comme le formulaire actuel.
"""

import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.audit.services import log_action
from apps.promotions.models import Coupon
from apps.shipping.models import City, ShippingZone
from apps.store_settings.models import StoreSettings

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "demo_store_config.json"
ZONE_NAME = "Maroc"


def dec(value):
    return None if value is None else Decimal(str(value))


class Command(BaseCommand):
    help = "Importe la configuration boutique du front (villes, livraison, code promo de démo)."

    def add_arguments(self, parser):
        parser.add_argument("--update", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        update = options["update"]
        done = []

        settings, created = StoreSettings.objects.get_or_create(pk=1)
        if created or update:
            settings.brand_name = data["brandName"]
            settings.whatsapp_number = data["whatsappNumber"]
            settings.max_qty_per_line = data["maxQtyPerLine"]
            settings.save()
            done.append("réglages")

        zone = ShippingZone.objects.filter(name=ZONE_NAME).first()
        if zone is None or update:
            zone, _ = ShippingZone.objects.update_or_create(
                name=ZONE_NAME,
                defaults={
                    "fee": dec(data["deliveryFee"]),
                    "free_over_subtotal": dec(data["freeDeliveryThreshold"]),
                    "is_default": True,
                    "is_active": True,
                },
            )
            ShippingZone.objects.exclude(pk=zone.pk).update(is_default=False)
            done.append(f"zone {ZONE_NAME} ({data['deliveryFee']} DH)")

        new_cities = 0
        for position, name in enumerate(data["cities"]):
            city, created = City.objects.get_or_create(name=name, defaults={"zone": zone, "position": position})
            new_cities += created
            if update and not created:
                City.objects.filter(pk=city.pk).update(position=position, is_active=True)
        done.append(f"{new_cities} ville(s) ajoutée(s)")

        for code, percent in data["promoCodes"].items():
            _, created = Coupon.objects.get_or_create(
                code=code.upper(),
                defaults={
                    "type": Coupon.Type.PERCENTAGE,
                    "value": dec(percent),
                    "note": "[DÉMO] importé de src/config/store.js — à supprimer ou remplacer avant la mise en ligne",
                },
            )
            if created:
                done.append(f"code {code} (-{percent} %)")

        log_action("store_config.import", changes={"done": done})
        self.stdout.write(self.style.SUCCESS("Configuration importée : " + ", ".join(done)))
