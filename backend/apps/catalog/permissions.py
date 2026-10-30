"""Qui peut faire quoi dans le catalogue (docs/ARCHITECTURE.md §6.2)."""

from apps.accounts.roles import Role
from apps.core.permissions import ReadWriteRoles

ALL_ROLES = frozenset(Role)
CATALOG_WRITE = frozenset({Role.OWNER, Role.ADMIN, Role.CONTENT_EDITOR})
CATALOG_DELETE = frozenset({Role.OWNER, Role.ADMIN})
COST_VIEW = frozenset({Role.OWNER, Role.ADMIN, Role.ANALYST})
COST_EDIT = frozenset({Role.OWNER, Role.ADMIN})

# Lecture : toute l'équipe · écriture : Propriétaire, Admin, Éditeur · suppression : Propriétaire, Admin
CATALOG_PERMISSION = ReadWriteRoles.of(read=ALL_ROLES, write=CATALOG_WRITE, delete=CATALOG_DELETE)
