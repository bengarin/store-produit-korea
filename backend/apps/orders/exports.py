"""Export Excel des commandes (openpyxl)."""

import io

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font

HEADERS = [
    "N° commande",
    "Date",
    "Statut",
    "Paiement",
    "Client",
    "Téléphone",
    "Ville",
    "Adresse",
    "Articles",
    "Sous-total (DH)",
    "Remise (DH)",
    "Livraison (DH)",
    "Total (DH)",
    "Code promo",
]
DANGEROUS_START = ("=", "+", "-", "@", "\t", "\r")


def safe_text(value: str) -> str:
    """
    Les noms et adresses viennent du public : un texte commençant par « = » serait exécuté comme
    formule par Excel (injection de formule). On le neutralise en le préfixant d'une apostrophe.
    """
    value = value or ""
    return "'" + value if value.startswith(DANGEROUS_START) else value


def orders_workbook(orders) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Commandes"
    ws.append(HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for o in orders:
        ws.append(
            [
                o.number,
                timezone.localtime(o.placed_at).strftime("%Y-%m-%d %H:%M"),
                o.get_status_display(),
                o.get_payment_status_display(),
                safe_text(o.ship_full_name),
                safe_text(o.ship_phone),
                safe_text(o.ship_city_label),
                safe_text(o.ship_address),
                o.item_count,
                float(o.subtotal),
                float(o.discount_total),
                float(o.shipping_fee),
                float(o.total),
                safe_text(o.coupon_code),
            ]
        )
    for column, width in zip("ABCDEFGHIJKLMN", (18, 17, 24, 30, 24, 15, 14, 40, 9, 14, 12, 13, 12, 12), strict=True):
        ws.column_dimensions[column].width = width
    ws.freeze_panes = "A2"
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
