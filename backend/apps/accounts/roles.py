"""
Les 5 rôles de l'équipe (docs/ARCHITECTURE.md §6.2). Chaque rôle = un groupe Django
(créé par la migration 0002). Un utilisateur a UN seul rôle.
"""

from django.db import models


class Role(models.TextChoices):
    OWNER = "owner", "Propriétaire"
    ADMIN = "admin", "Administrateur"
    ORDER_MANAGER = "order_manager", "Gestionnaire de commandes"
    CONTENT_EDITOR = "content_editor", "Éditeur de contenu"
    ANALYST = "analyst", "Analyste (lecture seule)"


ROLE_VALUES = frozenset(Role.values)
