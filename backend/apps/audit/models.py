from django.conf import settings
from django.db import models


class AppendOnlyQuerySet(models.QuerySet):
    """Interdit les modifications et suppressions en masse : le journal ne se réécrit pas."""

    def update(self, **kwargs):
        raise PermissionError("Le journal d'audit est en ajout seul.")

    def delete(self):
        raise PermissionError("Le journal d'audit est en ajout seul.")


class AuditLog(models.Model):
    """
    Trace d'une action importante (connexion, modification de prix, statut de commande,
    publication du thème…). Ne contient jamais de mot de passe ni de jeton.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="auteur",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,  # l'entrée survit à l'utilisateur
        related_name="audit_logs",
    )
    actor_email = models.EmailField("e-mail de l'auteur (copie)", max_length=254, blank=True)
    action = models.CharField("action", max_length=64, db_index=True)  # ex. "auth.login"
    target_type = models.CharField("type de cible", max_length=64, blank=True)  # ex. "accounts.user"
    target_id = models.CharField("identifiant de la cible", max_length=64, blank=True)
    changes = models.JSONField("détails", default=dict, blank=True)
    ip_address = models.GenericIPAddressField("adresse IP", null=True, blank=True)
    user_agent = models.CharField("navigateur", max_length=255, blank=True)
    created_at = models.DateTimeField("date", auto_now_add=True, db_index=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        verbose_name = "entrée d'audit"
        verbose_name_plural = "journal d'audit"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["target_type", "target_id"], name="audit_target_idx"),
            models.Index(fields=["actor", "created_at"], name="audit_actor_date_idx"),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} ({self.actor_email or 'système'})"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionError("Une entrée d'audit ne peut pas être modifiée.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Une entrée d'audit ne peut pas être supprimée.")
