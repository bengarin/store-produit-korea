import pytest
from django.contrib.auth.models import Group
from django.db import IntegrityError

from apps.accounts.models import User
from apps.accounts.roles import Role


@pytest.mark.django_db
def test_les_5_roles_existent_apres_migration():
    assert set(Group.objects.values_list("name", flat=True)) >= {
        "owner",
        "admin",
        "order_manager",
        "content_editor",
        "analyst",
    }
    assert len(Role.values) == 5


@pytest.mark.django_db
def test_email_normalise_et_unique():
    User.objects.create_user(email="Equipe@Exemple.MA", password="x")
    assert User.objects.get().email == "equipe@exemple.ma"
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="equipe@exemple.ma", password="x")


def test_email_obligatoire():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="x")


@pytest.mark.django_db
def test_mot_de_passe_hache():
    user = User.objects.create_user(email="a@b.ma", password="Secret-12345678")
    assert user.password != "Secret-12345678"
    assert user.check_password("Secret-12345678")


@pytest.mark.django_db
def test_un_seul_role_par_utilisateur(make_user):
    user = make_user(role=Role.ANALYST)
    user.set_role(Role.ORDER_MANAGER)
    user = User.objects.get(pk=user.pk)
    assert user.role == Role.ORDER_MANAGER
    assert user.groups.count() == 1
    assert user.is_staff


@pytest.mark.django_db
def test_sans_role_pas_d_acces(make_user):
    user = make_user(role=None)
    assert user.role is None
    assert not user.is_staff


@pytest.mark.django_db
def test_superutilisateur_est_proprietaire():
    user = User.objects.create_superuser(email="owner@b.ma", password="x")
    assert user.role == Role.OWNER


@pytest.mark.django_db
def test_commande_create_staff_user(monkeypatch):
    from django.core.management import call_command

    from apps.audit.models import AuditLog

    monkeypatch.setenv("MPC_STAFF_PASSWORD", "Tres-Long-Mot-De-Passe-2026")
    call_command("create_staff_user", email="Chef@Exemple.ma", role="owner")
    user = User.objects.get(email="chef@exemple.ma")
    assert user.role == Role.OWNER
    assert user.check_password("Tres-Long-Mot-De-Passe-2026")
    log = AuditLog.objects.get(action="user.create")
    assert "Tres-Long" not in str(log.changes)


@pytest.mark.django_db
def test_commande_refuse_mot_de_passe_faible(monkeypatch):
    from django.core.management import CommandError, call_command

    monkeypatch.setenv("MPC_STAFF_PASSWORD", "123")
    with pytest.raises(CommandError):
        call_command("create_staff_user", email="a@b.ma", role="admin")
