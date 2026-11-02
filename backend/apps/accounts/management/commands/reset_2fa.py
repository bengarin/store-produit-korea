"""
Récupération de compte (téléphone ET codes de secours perdus) — réservé à la personne qui administre le serveur,
APRÈS vérification de l'identité par un autre moyen (voir docs/PRODUCTION.md, « Récupération de compte ») :

    python manage.py reset_2fa --email personne@exemple.ma

Supprime la 2FA du compte et ferme TOUTES ses sessions. Si son rôle impose la 2FA, elle devra la réactiver
à la prochaine connexion. Action enregistrée dans le journal d'audit.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.accounts import twofactor
from apps.accounts.models import User
from apps.audit.services import log_action


class Command(BaseCommand):
    help = "Réinitialise la double authentification d'un compte et ferme ses sessions."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)

    def handle(self, *args, email, **options):
        user = User.objects.filter(email__iexact=email.strip()).first()
        if user is None:
            raise CommandError("Aucun compte avec cet e-mail.")
        twofactor.disable(user)
        sessions = twofactor.revoke_sessions(user)
        log_action("auth.otp_reset_by_server", target=user, changes={"sessionsRevoked": sessions})
        self.stdout.write(self.style.SUCCESS(f"2FA réinitialisée pour {user.email} ; {sessions} session(s) fermée(s)."))
