"""Matrice rôle × permission sur une vue de test (le socle que toutes les vues admin utiliseront)."""

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.roles import Role
from apps.core.permissions import HasRole, IsStaffMember


class OwnerAdminView(APIView):
    permission_classes = [HasRole.of(Role.OWNER, Role.ADMIN)]

    def get(self, request):
        from rest_framework.response import Response

        return Response({"ok": True})


class DefaultView(APIView):  # aucune permission déclarée => réglage par défaut (fermé)
    def get(self, request):
        from rest_framework.response import Response

        return Response({"ok": True})


def call(view, user=None):
    request = APIRequestFactory().get("/")
    if user is not None:
        force_authenticate(request, user=user)
    return view.as_view()(request).status_code


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Role.OWNER, 200),
        (Role.ADMIN, 200),
        (Role.ORDER_MANAGER, 403),
        (Role.CONTENT_EDITOR, 403),
        (Role.ANALYST, 403),
        (None, 403),
    ],
)
def test_matrice_roles(make_user, role, expected):
    assert call(OwnerAdminView, make_user(role=role)) == expected


@pytest.mark.django_db
def test_anonyme_refuse():
    assert call(OwnerAdminView) == 403
    assert call(DefaultView) == 403


@pytest.mark.django_db
@pytest.mark.parametrize("role", list(Role))
def test_par_defaut_tout_membre_de_l_equipe_et_seulement_lui(make_user, role):
    assert call(DefaultView, make_user(role=role)) == 200


@pytest.mark.django_db
def test_utilisateur_inactif_refuse(make_user):
    user = make_user(role=Role.OWNER)
    user.is_active = False
    assert not IsStaffMember().has_permission(type("R", (), {"user": user})(), None)
    assert isinstance(User.objects.get(pk=user.pk), User)
