"""
Permissions par rôle.

Par défaut, toute vue de l'API exige un membre de l'équipe (rôle défini) : une vue publique
doit déclarer `permission_classes = [AllowAny]`. Le serveur reste l'unique autorité :
le front ne fait que masquer les boutons.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.roles import Role


class IsStaffMember(BasePermission):
    """Utilisateur connecté, actif, avec un rôle de l'équipe."""

    message = "Vous n'avez pas les droits pour cette action."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.role is not None)


class HasRole(IsStaffMember):
    """Restreint une vue à certains rôles. Usage : `permission_classes = [HasRole.of(Role.OWNER)]`."""

    allowed_roles: frozenset = frozenset()

    @classmethod
    def of(cls, *roles: Role):
        return type("HasRole_" + "_".join(r.value for r in roles), (cls,), {"allowed_roles": frozenset(roles)})

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in self.allowed_roles
