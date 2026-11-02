"""
Permissions par rôle.

Par défaut, toute vue de l'API exige un membre de l'équipe (rôle défini) : une vue publique
doit déclarer `permission_classes = [AllowAny]`. Le serveur reste l'unique autorité :
le front ne fait que masquer les boutons.
"""

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from apps.accounts.roles import Role


class OtpRequired(PermissionDenied):
    default_code = "otp_required"


class OtpSetupRequired(PermissionDenied):
    default_code = "otp_setup_required"


class IsStaffMember(BasePermission):
    """
    Utilisateur connecté, actif, avec un rôle de l'équipe ET double authentification validée pour cette
    session (si elle est activée, ou obligatoire pour son rôle). Les routes de 2FA déclarent
    `allow_unverified = True` pour rester accessibles avant la saisie du code.
    """

    message = "Vous n'avez pas les droits pour cette action."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active and user.role is not None):
            return False
        if getattr(view, "allow_unverified", False):
            return True
        from apps.accounts import twofactor

        state = twofactor.status(request)
        if state == "required":
            raise OtpRequired()
        if state == "setup_required":
            raise OtpSetupRequired()
        return True


class HasRole(IsStaffMember):
    """Restreint une vue à certains rôles. Usage : `permission_classes = [HasRole.of(Role.OWNER)]`."""

    allowed_roles: frozenset = frozenset()

    @classmethod
    def of(cls, *roles: Role):
        return type("HasRole_" + "_".join(r.value for r in roles), (cls,), {"allowed_roles": frozenset(roles)})

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in self.allowed_roles


SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


class ReadWriteRoles(IsStaffMember):
    """
    Rôles différents pour la lecture (GET) et l'écriture (POST/PUT/PATCH/DELETE).
    Usage : `permission_classes = [ReadWriteRoles.of(read=ALL_ROLES, write={Role.OWNER, Role.ADMIN})]`
    """

    read_roles: frozenset = frozenset()
    write_roles: frozenset = frozenset()
    delete_roles: frozenset | None = None  # None = mêmes rôles que l'écriture

    @classmethod
    def of(cls, *, read, write, delete=None):
        attrs = {"read_roles": frozenset(read), "write_roles": frozenset(write)}
        if delete is not None:
            attrs["delete_roles"] = frozenset(delete)
        return type("ReadWriteRoles", (cls,), attrs)

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            allowed = self.read_roles
        elif request.method == "DELETE" and self.delete_roles is not None:
            allowed = self.delete_roles
        else:
            allowed = self.write_roles
        return request.user.role in allowed
