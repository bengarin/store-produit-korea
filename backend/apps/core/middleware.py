"""IP réelle du visiteur et en-têtes de sécurité."""

import contextlib
import ipaddress

from django.conf import settings


class TrustedProxyMiddleware:
    """
    Derrière un ou plusieurs proxys DE CONFIANCE (nginx, hébergeur), REMOTE_ADDR est l'adresse du proxy.
    Si TRUSTED_PROXY_COUNT = n > 0, l'IP réelle est la n-ième adresse en partant de la DROITE de
    X-Forwarded-For (celle ajoutée par notre premier proxy) ; ce qu'un client met à gauche est ignoré.
    TRUSTED_PROXY_COUNT = 0 (défaut, accès direct) : X-Forwarded-For est totalement ignoré.
    Tout le reste du code (limites de débit, verrouillage, journal d'audit, commandes) lit REMOTE_ADDR.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.count = int(getattr(settings, "TRUSTED_PROXY_COUNT", 0) or 0)

    def __call__(self, request):
        if self.count > 0:
            parts = [p.strip() for p in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if p.strip()]
            if len(parts) >= self.count:
                candidate = parts[-self.count]
                # En-tête invalide : on garde l'adresse du proxy (limite plus stricte, jamais plus large).
                with contextlib.suppress(ValueError):
                    request.META["REMOTE_ADDR"] = str(ipaddress.ip_address(candidate))
        return self.get_response(request)
