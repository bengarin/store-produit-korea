"""Blog : toute l'équipe lit ; Propriétaire, Admin, Éditeur écrivent ; suppression : Propriétaire, Admin."""

from apps.catalog.permissions import ALL_ROLES, CATALOG_DELETE, CATALOG_WRITE
from apps.core.permissions import ReadWriteRoles

BLOG_PERMISSION = ReadWriteRoles.of(read=ALL_ROLES, write=CATALOG_WRITE, delete=CATALOG_DELETE)
