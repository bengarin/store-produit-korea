"""
Factures : émises à la livraison, numérotées par année (PRÉFIXE-AAAA-000001), contenu figé.

Montants : le total de la facture = total de la commande payé par le client (prix TTC, recalculé par le serveur).
Si un taux de TVA est configuré : HT = TTC / (1 + taux) ; TVA = TTC − HT.
Sans taux : aucune TVA affichée ni supposée.
[À VÉRIFIER avec un comptable : régime de TVA, mentions obligatoires, avoirs.]
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.core.money import money
from apps.store_settings.models import StoreSettings

from .models import Invoice, InvoiceSequence, Order

SELLER_FIELDS = (
    "brand_name",
    "legal_name",
    "legal_address",
    "ice",
    "rc",
    "if_number",
    "patente",
    "contact_phone",
    "contact_email",
    "invoice_footer",
)


def missing_legal_info(settings: StoreSettings) -> list[str]:
    labels = {"legal_name": "raison sociale", "legal_address": "adresse", "ice": "ICE", "rc": "RC", "if_number": "IF"}
    return [label for field, label in labels.items() if not getattr(settings, field)]


def vat_breakdown(total: Decimal, rate: Decimal | None):
    """(HT, TVA) d'un total TTC ; (None, None) si aucun taux n'est configuré."""
    if rate is None:
        return None, None
    excl = money(total / (1 + Decimal(rate) / 100))
    return excl, money(total - excl)


@transaction.atomic
def issue_invoice(order: Order) -> Invoice:
    """Émet la facture d'une commande LIVRÉE (idempotent : renvoie la facture existante)."""
    existing = Invoice.objects.filter(order=order).first()
    if existing:
        return existing
    if order.status != Order.Status.DELIVERED:
        raise ValueError("Une facture n'est émise que pour une commande livrée.")
    settings = StoreSettings.load()
    year = timezone.localdate().year
    seq, _ = InvoiceSequence.objects.select_for_update().get_or_create(year=year)
    seq.last_value += 1
    seq.save(update_fields=["last_value"])
    excl, vat = vat_breakdown(order.total, settings.vat_rate)
    return Invoice.objects.create(
        order=order,
        number=f"{settings.invoice_prefix}-{year}-{seq.last_value:06d}",
        year=year,
        sequence=seq.last_value,
        seller={f: getattr(settings, f) for f in SELLER_FIELDS},
        total=order.total,
        vat_rate=settings.vat_rate,
        total_excl_vat=excl,
        vat_amount=vat,
    )
