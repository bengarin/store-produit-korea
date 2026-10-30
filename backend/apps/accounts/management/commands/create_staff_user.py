"""
Crée (ou met à jour) un membre de l'équipe avec un rôle.

    python manage.py create_staff_user --email owner@exemple.ma --role owner

Le mot de passe est demandé de façon masquée (jamais en argument : il resterait dans
l'historique du terminal). Pour un script, utiliser la variable d'environnement
MPC_STAFF_PASSWORD.
"""

import getpass
import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.accounts.roles import Role
from apps.audit.services import log_action


class Command(BaseCommand):
    help = "Crée ou met à jour un membre de l'équipe (e-mail + rôle)."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--role", required=True, choices=Role.values)
        parser.add_argument("--first-name", default="")
        parser.add_argument("--last-name", default="")

    def _read_password(self, user):
        password = os.environ.get("MPC_STAFF_PASSWORD")
        if not password:
            password = getpass.getpass("Mot de passe : ")
            if password != getpass.getpass("Confirmez : "):
                raise CommandError("Les mots de passe ne correspondent pas.")
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc
        return password

    @transaction.atomic
    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        user = User.objects.filter(email=email).first()
        created = user is None
        if created:
            user = User(email=email)
        user.first_name = options["first_name"] or user.first_name
        user.last_name = options["last_name"] or user.last_name
        user.set_password(self._read_password(user))
        user.is_active = True
        user.save()
        user.set_role(Role(options["role"]))
        log_action(
            "user.create" if created else "user.update",
            target=user,
            changes={"role": options["role"], "source": "commande create_staff_user"},
        )
        verb = "créé" if created else "mis à jour"
        self.stdout.write(
            self.style.SUCCESS(f"Utilisateur {email} {verb} avec le rôle « {Role(options['role']).label} ».")
        )
