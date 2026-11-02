"""Retente les e-mails en attente ou en échec (5 essais max.). À planifier (cron / timer systemd) toutes les 10 min."""

from django.core.management.base import BaseCommand

from apps.notifications.services import configured, retry_pending


class Command(BaseCommand):
    help = "Envoie les e-mails en attente ou en échec."

    def handle(self, *args, **options):
        if not configured():
            self.stdout.write("E-mail non configuré (EMAIL_HOST / DEFAULT_FROM_EMAIL) : rien à envoyer.")
            return
        self.stdout.write(f"{retry_pending()} e-mail(s) envoyé(s).")
