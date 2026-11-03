"""Sessions de l'équipe : fermeture de toutes les sessions d'un compte (appareil perdu, mot de passe compromis)."""

from django.contrib.sessions.models import Session
from django.utils import timezone


def revoke_sessions(user, keep_session_key: str | None = None) -> int:
    """Ferme toutes les sessions de l'utilisateur (sauf, éventuellement, la session en cours)."""
    count = 0
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        if session.session_key == keep_session_key:
            continue
        if session.get_decoded().get("_auth_user_id") == str(user.pk):
            session.delete()
            count += 1
    return count
