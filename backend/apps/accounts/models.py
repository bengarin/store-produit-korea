from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import Group, PermissionsMixin
from django.db import models, transaction
from django.utils import timezone

from .managers import UserManager
from .roles import ROLE_VALUES, Role


class User(AbstractBaseUser, PermissionsMixin):
    """
    Membre de l'équipe (administration). Connexion par e-mail.
    Les clients de la boutique ne sont PAS des utilisateurs (app `customers`, phase 2).
    Suppression déconseillée : désactiver (`is_active=False`) pour garder la traçabilité.
    """

    email = models.EmailField("e-mail", max_length=254, unique=True)
    first_name = models.CharField("prénom", max_length=150, blank=True)
    last_name = models.CharField("nom", max_length=150, blank=True)
    is_active = models.BooleanField("actif", default=True)
    is_staff = models.BooleanField("équipe", default=False)
    date_joined = models.DateTimeField("créé le", default=timezone.now)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["email"]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def role(self) -> Role | None:
        """Rôle de l'utilisateur (superutilisateur = Propriétaire). None = aucun accès admin."""
        if not self.pk:
            return None
        if not hasattr(self, "_role_cache"):
            if self.is_superuser:
                self._role_cache = Role.OWNER
            else:
                names = self.groups.filter(name__in=ROLE_VALUES).values_list("name", flat=True)
                found = next(iter(names), None)
                self._role_cache = Role(found) if found else None
        return self._role_cache

    @transaction.atomic
    def set_role(self, role: Role | None):
        """Attribue un rôle unique (retire les autres) et marque le compte comme membre de l'équipe."""
        self.groups.remove(*Group.objects.filter(name__in=ROLE_VALUES))
        if role is not None:
            self.groups.add(Group.objects.get(name=Role(role).value))
        self.is_staff = role is not None or self.is_superuser
        self.save(update_fields=["is_staff", "updated_at"])
        self.__dict__.pop("_role_cache", None)
