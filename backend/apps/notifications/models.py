from django.db import models


class EmailLog(models.Model):
    """
    Journal de chaque e-mail (envoyé, en échec, ou NON envoyé car l'e-mail n'est pas configuré).
    Un échec n'empêche jamais une commande : il est noté ici et retenté par `send_pending_emails`.
    """

    class Kind(models.TextChoices):
        ORDER_ADMIN = "order_admin", "Nouvelle commande (équipe)"
        ORDER_CUSTOMER = "order_customer", "Confirmation de commande (client)"
        STATUS_CUSTOMER = "status_customer", "Suivi de commande (client)"
        TEST = "test", "E-mail de test"

    class Status(models.TextChoices):
        PENDING = "pending", "À envoyer"
        SENT = "sent", "Envoyé"
        FAILED = "failed", "Échec"
        SKIPPED = "skipped", "Non envoyé (e-mail non configuré)"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    to = models.CharField(max_length=500)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    error = models.CharField(max_length=300, blank=True)
    order = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "e-mail"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status", "created_at"], name="email_status_idx")]

    def __str__(self):
        return f"{self.kind} → {self.to} ({self.status})"
