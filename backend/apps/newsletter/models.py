from django.db import models


class Subscriber(models.Model):
    """
    Inscription à la newsletter (formulaire de la boutique). Le consentement est OBLIGATOIRE et le texte exact
    accepté est conservé (preuve du consentement, loi 09-08 — [À VÉRIFIER avec un juriste / la CNDP]).
    Aucun e-mail n'est envoyé par le site : la liste s'exporte vers l'outil d'e-mailing choisi.
    """

    email = models.EmailField("e-mail", max_length=254, unique=True)
    consent_text = models.CharField("texte de consentement accepté", max_length=240)
    consented_at = models.DateTimeField("consentement le", auto_now_add=True)
    source = models.CharField(max_length=40, default="boutique")

    class Meta:
        verbose_name = "inscrit à la newsletter"
        ordering = ["-consented_at", "-id"]

    def __str__(self):
        return self.email
