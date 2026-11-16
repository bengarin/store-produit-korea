"""
Données de démarrage jointes à chaque page de la boutique (P1 de l'audit) : produits, catégories, filtres,
configuration et thème publiés — exactement les réponses des API publiques que l'application appelait au
démarrage. Elle les lit tout de suite, sans attendre 5 allers-retours réseau avant le premier affichage.
Rien de privé : uniquement ce que les API publiques renvoient déjà.
"""

import json

from apps.catalog import public as catalog
from apps.orders.public import store_config_payload
from apps.themes import services as themes


def store_data(products: list | None = None) -> dict:
    current = themes.latest_version()
    theme = (
        {"version": None, "theme": None, "media": {}}
        if current is None
        else {"version": current.number, "theme": current.data, "media": themes.media_payload(current.data)}
    )
    if products is None:
        products = [catalog.product_payload(p) for p in catalog.public_products_queryset()]
    return {
        "products": products,
        "categories": [catalog.category_payload(c) for c in catalog.visible_categories()],
        "filters": catalog.filter_groups_payload(),
        "config": store_config_payload(),
        "theme": theme,
    }


def data_script(data: dict) -> str:
    """Bloc de données JSON (non exécuté) ; < > & échappés : impossible de fermer la balise depuis le contenu."""
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f'<script id="mpc-data" type="application/json">{text}</script>'
