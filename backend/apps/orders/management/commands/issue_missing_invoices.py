"""
Émet les factures des commandes DÉJÀ livrées avant la phase 7 (aucune facture n'existait alors).
Par défaut : simulation (rien n'est écrit). Avec --apply : émission réelle, dans l'ordre des livraisons.

    python manage.py issue_missing_invoices           # liste ce qui serait émis
    python manage.py issue_missing_invoices --apply   # émet (à faire seulement avec l'accord du propriétaire)
"""

from django.core.management.base import BaseCommand

from apps.orders.invoicing import issue_invoice
from apps.orders.models import Order


class Command(BaseCommand):
    help = "Émet les factures manquantes des commandes livrées (simulation par défaut)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Émettre réellement les factures.")

    def handle(self, *args, apply, **options):
        todo = Order.objects.filter(status=Order.Status.DELIVERED, invoice__isnull=True).order_by("delivered_at", "id")
        self.stdout.write(f"{todo.count()} commande(s) livrée(s) sans facture.")
        for order in todo:
            if apply:
                invoice = issue_invoice(order)
                self.stdout.write(f"  {order.number} → {invoice.number}")
            else:
                self.stdout.write(f"  {order.number} (simulation)")
        if not apply:
            self.stdout.write(self.style.WARNING("Simulation : relancez avec --apply pour émettre."))
