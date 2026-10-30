import pytest
from django.test import RequestFactory

from apps.audit.models import AuditLog
from apps.audit.services import REDACTED, log_action, scrub


def test_scrub_masque_les_secrets_recursivement():
    data = {
        "email": "a@b.ma",
        "password": "x",
        "nested": {"newPassword": "y", "csrfToken": "z"},
        "list": [{"api_key": 1}],
    }
    cleaned = scrub(data)
    assert cleaned["email"] == "a@b.ma"
    assert cleaned["password"] == REDACTED
    assert cleaned["nested"] == {"newPassword": REDACTED, "csrfToken": REDACTED}
    assert cleaned["list"] == [{"api_key": REDACTED}]


@pytest.mark.django_db
def test_log_action_enregistre_auteur_cible_ip(make_user):
    user = make_user(email="a@exemple.ma")
    request = RequestFactory().post("/x", REMOTE_ADDR="203.0.113.7", HTTP_USER_AGENT="Test/1.0")
    entry = log_action("user.update", actor=user, target=user, changes={"role": ["analyst", "admin"]}, request=request)
    assert entry.actor_email == "a@exemple.ma"
    assert (entry.target_type, entry.target_id) == ("accounts.user", str(user.pk))
    assert entry.ip_address == "203.0.113.7" and entry.user_agent == "Test/1.0"


@pytest.mark.django_db
def test_journal_en_ajout_seul(make_user):
    entry = log_action("test.action")
    entry.action = "modifie"
    with pytest.raises(PermissionError):
        entry.save()
    with pytest.raises(PermissionError):
        entry.delete()
    with pytest.raises(PermissionError):
        AuditLog.objects.all().update(action="x")
    with pytest.raises(PermissionError):
        AuditLog.objects.all().delete()


@pytest.mark.django_db
def test_l_entree_survit_a_la_suppression_de_l_auteur(make_user):
    user = make_user(email="parti@exemple.ma")
    entry = log_action("test.action", actor=user)
    user.delete()
    entry = AuditLog.objects.get(pk=entry.pk)
    assert entry.actor is None and entry.actor_email == "parti@exemple.ma"
