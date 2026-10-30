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

# --- Phase 2 -------------------------------------------------------------
_OPS_READ = frozenset({Role.OWNER, Role.ADMIN, Role.ORDER_MANAGER, Role.ANALYST})
_OPS_WRITE = frozenset({Role.OWNER, Role.ADMIN, Role.ORDER_MANAGER})
_SETTINGS_WRITE = frozenset({Role.OWNER, Role.ADMIN})

# Commandes et clients : l'Éditeur de contenu n'y a pas accès (données personnelles).
ORDERS_PERMISSION = ReadWriteRoles.of(read=_OPS_READ, write=_OPS_WRITE)
# Stock : toute l'équipe lit, ajustement par Propriétaire, Admin, Gestionnaire de commandes.
INVENTORY_PERMISSION = ReadWriteRoles.of(read=ALL_ROLES, write=_OPS_WRITE)
# Codes promo, livraison, réglages : modification par Propriétaire et Admin.
SETTINGS_PERMISSION = ReadWriteRoles.of(read=_OPS_READ, write=_SETTINGS_WRITE)
