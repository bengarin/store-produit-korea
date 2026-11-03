"""
Ferme toutes les sessions d'un compte (ordinateur perdu, mot de passe compromis) :

    python manage.py revoke_sessions --email personne@exemple.ma [--deactivate]

--deactivate : désactive aussi le compte (plus aucune connexion possible jusqu'à réactivation).
"""

from django.core.management.base import BaseCommand, CommandError

from apps.accounts import sessions
from apps.accounts.models import User
from apps.audit.services import log_action


class Command(BaseCommand):
    help = "Ferme toutes les sessions d'un compte (et peut le désactiver)."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--deactivate", action="store_true")

    def handle(self, *args, email, deactivate, **options):
        user = User.objects.filter(email__iexact=email.strip()).first()
        if user is None:
            raise CommandError("Aucun compte avec cet e-mail.")
        if deactivate:
            user.is_active = False
            user.save(update_fields=["is_active", "updated_at"])
        count = sessions.revoke_sessions(user)
        log_action("auth.sessions_revoked_by_server", target=user, changes={"count": count, "deactivated": deactivate})
        self.stdout.write(
            self.style.SUCCESS(
                f"{count} session(s) fermée(s) pour {user.email}{' ; compte désactivé' if deactivate else ''}."
            )
        )
