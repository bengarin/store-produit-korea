"""
Format PUBLIC d'un produit : identique à celui du catalogue local du front
(src/data/local + src/services/productService.js → normalizeProduct) — voir docs/BACKEND.md.

- `id` = slug (le panier, les favoris et les liens du front utilisent cet identifiant)
- le coût, le stock exact et les brouillons ne sont JAMAIS exposés
"""

from decimal import Decimal

from django.db.models import Avg, Count, Prefetch, Q

from .models import (
    Category,
    Collection,
    FilterGroup,
    FilterOption,
    Product,
    ProductCategory,
    ProductImage,
    ProductMarketingImage,
    ProductOption,
    Variant,
)

# Avis produits APPROUVÉS uniquement (statut de apps.reviews.ProductReview) : jamais d'avis en attente ou refusé.
APPROVED_REVIEWS = Q(reviews__status="approved")

# Valeur de filtre visible = valeur visible ET groupe visible (masquer un groupe masque toutes ses valeurs).
VISIBLE_FILTER_OPTION = Q(is_active=True, group__is_active=True)


def number(value: Decimal | None):
    if value is None:
        return None
    return int(value) if value == value.to_integral_value() else float(value)


def image_payload(image: ProductImage | None, position: str = ""):
    if image is None:
        return None
    data = {"src": image.media.url, "alt": image.alt or image.media.alt, "kind": image.kind, "fit": image.fit}
    if image.media.file_640:
        data["src640"] = image.media.url_640
    focal = position or image.focal_position
    if focal:
        data["position"] = focal
    return data


# Catégorie visible = active ET (catégorie principale OU parente active) : masquer une catégorie masque
# aussi ses sous-catégories dans le menu et les filtres. Les produits restent dans l'administration.
VISIBLE_CATEGORY = Q(is_active=True) & (Q(parent__isnull=True) | Q(parent__is_active=True))
VISIBLE_LINK = Q(category__is_active=True) & (Q(category__parent__isnull=True) | Q(category__parent__is_active=True))


def visible_categories():
    """Catégories du menu, dans l'ordre : chaque catégorie principale puis ses sous-catégories."""
    rows = list(Category.objects.filter(VISIBLE_CATEGORY).select_related("parent"))
    tops = [c for c in rows if c.parent_id is None]
    ordered = []
    for top in tops:
        ordered.append(top)
        ordered += [c for c in rows if c.parent_id == top.pk]
    return ordered


def public_products_queryset(statuses=(Product.Status.ACTIVE,)):
    """Produits au format public. `statuses` élargi uniquement pour l'aperçu de l'administration."""
    return (
        Product.objects.filter(status__in=statuses)
        # Note des cartes produits : calculée sur les seuls avis approuvés (une seule jointure → pas de doublons).
        .annotate(
            approved_review_count=Count("reviews", filter=APPROVED_REVIEWS),
            approved_review_avg=Avg("reviews__rating", filter=APPROVED_REVIEWS),
        )
        .select_related("hover_image__media", "scene_image__media", "og_image")
        .prefetch_related(
            Prefetch(
                "category_links",
                queryset=ProductCategory.objects.filter(VISIBLE_LINK).select_related("category"),
            ),
            "highlights",
            Prefetch("images", queryset=ProductImage.objects.filter(in_gallery=True).select_related("media")),
            Prefetch(
                "variants",
                queryset=Variant.objects.select_related("image__media").prefetch_related("option_values__option"),
            ),
            Prefetch("options", queryset=ProductOption.objects.prefetch_related("values")),
            Prefetch(
                "marketing_images",
                queryset=ProductMarketingImage.objects.filter(is_active=True).select_related("media"),
            ),
            Prefetch(
                "filter_options", queryset=FilterOption.objects.filter(VISIBLE_FILTER_OPTION).select_related("group")
            ),
            Prefetch("collections", queryset=Collection.objects.filter(is_active=True)),
        )
    )


def marketing_payload(product: Product) -> list:
    """Visuels marketing publics (actifs ; avant/après seulement si confirmés authentiques), dans l'ordre."""
    items = []
    for m in product.marketing_images.all():
        if not m.is_public:
            continue
        item = {
            "id": m.pk,
            "category": m.category,
            "language": m.language,
            "src": m.media.url,
            "width": m.media.width,
            "height": m.media.height,
            "alt": m.alt or m.title or m.media.alt,
        }
        if m.media.file_640:
            item["src640"] = m.media.url_640
        if m.title:
            item["title"] = m.title
        if m.description:
            item["description"] = m.description
        items.append(item)
    return items


def availability(variant: Variant) -> str:
    """
    État public d'une variante, sans publier la quantité :
    - "available"    : commandable maintenant
    - "out_of_stock" : stock suivi et épuisé (0)
    - "unavailable"  : stock non renseigné (NULL) — jamais traité comme disponible
    """
    if variant.is_available:
        return "available"
    return "unavailable" if variant.stock_quantity is None else "out_of_stock"


def product_payload(product: Product) -> dict:
    gallery = [image_payload(i) for i in product.images.all()]
    main = gallery[0] if gallery else None
    scene = image_payload(product.scene_image) if product.scene_image_id else main
    hover = image_payload(product.hover_image, product.hover_image_position) if product.hover_image_id else None
    variants = list(product.variants.all())
    default = next((v for v in variants if v.is_default), variants[0] if variants else None)
    payload = {
        "id": product.slug,
        "slug": product.slug,
        "brand": product.brand,
        "name": product.name,
        "displayName": product.public_name,
        "cardLine": product.short_description,
        "price": number(default.price) if default else None,
        "compareAtPrice": number(default.compare_at_price) if default else None,
        "categories": [link.category.slug for link in product.category_links.all()],
        "summary": product.summary,
        "descriptionHtml": product.description_html,
        "highlights": [{"icon": h.icon, "label": h.label} for h in product.highlights.all()],
        "ingredients": product.ingredients,
        "usage": product.usage_steps,
        "benefits": product.benefits,
        "skinTypes": product.skin_types,
        # Filtres de la page produits (Admin → Filtres) : « groupe:valeur », valeurs visibles uniquement.
        "filters": [f"{o.group.slug}:{o.slug}" for o in product.filter_options.all()],
        # Collections visibles (Admin → Collections) : un produit peut être dans plusieurs, une seule fiche.
        "collections": [c.slug for c in product.collections.all()],
        # Première mise en ligne : tri « Nouveautés ».
        "publishedAt": product.published_at.isoformat() if product.published_at else None,
        "stock": None,  # quantité exacte volontairement non publiée
        "inStock": any(v.is_available for v in variants),
        "cardImage": main,
        "mainImage": main,
        "galleryImages": gallery,
        "image": scene,
        "sceneImage": scene,
        "hoverImage": hover,
        "options": [{"name": o.name, "values": [v.value for v in o.values.all()]} for o in product.options.all()],
        "variants": [
            {
                "id": v.pk,
                "title": v.title,
                "sku": v.sku,
                "price": number(v.price),
                "compareAtPrice": number(v.compare_at_price),
                "available": v.is_available,
                "availability": availability(v),
                "isDefault": v.is_default,
                "options": {ov.option.name: ov.value for ov in v.option_values.all()},
                "image": image_payload(v.image) if v.image_id else None,
            }
            for v in variants
        ],
        # Contenus arabes saisis dans l'administration (seulement ceux qui sont remplis).
        "seo": {
            "title": product.seo_title or product.public_name,
            "description": product.seo_description or product.short_description or product.summary[:160],
            "image": product.og_image.url if product.og_image_id else (main["src"] if main else None),
        },
    }
    # Note moyenne et nombre d'avis APPROUVÉS : présents seulement s'il en existe (jamais de note inventée).
    review_count = getattr(product, "approved_review_count", 0) or 0
    review_avg = getattr(product, "approved_review_avg", None)
    if review_count and review_avg is not None:
        payload["reviews"] = {"count": review_count, "average": round(float(review_avg), 1)}
    # Pays de fabrication : seulement s'il a été renseigné (jamais supposé à partir de la marque).
    if product.origin_country:
        payload["origin"] = product.origin_country
    # Visuels marketing (colonne de droite de la fiche) : présents seulement s'il y en a.
    marketing = marketing_payload(product)
    if marketing:
        payload["marketing"] = marketing
    # Contenus arabes saisis dans l'administration : présents seulement s'il y en a (sinon le français s'affiche).
    arabic = arabic_payload(product)
    if arabic:
        payload["translations"] = {"ar": arabic}
    return payload


def arabic_payload(product: Product) -> dict:
    """Champs arabes remplis ; un champ absent = afficher le français. Pictos : même ordre, null si non traduit."""
    data = {
        "displayName": product.display_name_ar,
        "cardLine": product.short_description_ar,
        "summary": product.summary_ar,
        "descriptionHtml": product.description_html_ar,
        "ingredients": product.ingredients_ar,
        "usage": product.usage_steps_ar,
        "benefits": product.benefits_ar,
        "skinTypes": product.skin_types_ar,
    }
    out = {k: v for k, v in data.items() if v}
    labels = [h.label_ar or None for h in product.highlights.all()]
    if any(labels):
        out["highlights"] = labels
    return out


def category_payload(category: Category) -> dict:
    payload = {"id": category.slug, "label": category.name}
    if category.parent_id:
        payload["parent"] = category.parent.slug  # sous-catégorie : rangée sous sa catégorie dans le menu
    if category.name_ar:
        payload["translations"] = {"ar": {"label": category.name_ar}}
    return payload


def _label(obj) -> dict:
    data = {"id": obj.slug, "label": obj.name}
    if obj.name_ar:
        data["translations"] = {"ar": {"label": obj.name_ar}}
    return data


def filter_groups_payload() -> list:
    """Groupes de filtres visibles avec leurs valeurs visibles, dans l'ordre de l'admin (groupes vides omis)."""
    groups = FilterGroup.objects.filter(is_active=True).prefetch_related(
        Prefetch("options", queryset=FilterOption.objects.filter(is_active=True))
    )
    out = []
    for g in groups:
        options = [_label(o) for o in g.options.all()]
        if options:
            out.append({**_label(g), "options": options})
    return out


ACTIVE_PRODUCTS = Q(products__status=Product.Status.ACTIVE)


def visible_collections(include_empty: bool = False):
    """
    Collections affichées dans la boutique : visibles ET contenant au moins un produit en ligne (dans l'ordre).
    `include_empty` : aussi les collections visibles encore vides (onglets de l'accueil, avec un message « bientôt »).
    """
    qs = (
        Collection.objects.filter(is_active=True)
        .select_related("image")
        .annotate(product_count=Count("products", filter=ACTIVE_PRODUCTS, distinct=True))
        .order_by("position", "id")  # l'ordre du modèle est ignoré par Django dans une requête avec Count
    )
    return qs if include_empty else qs.filter(product_count__gt=0)


def _fallback_image(collection: Collection):
    """Sans image choisie : photo principale du premier produit en ligne de la collection."""
    first = (
        collection.products.filter(status=Product.Status.ACTIVE)
        .order_by("position", "id")
        .prefetch_related(
            Prefetch("images", queryset=ProductImage.objects.filter(in_gallery=True).select_related("media"))
        )
        .first()
    )
    images = list(first.images.all()) if first else []
    return image_payload(images[0]) if images else None


def collection_payload(collection: Collection) -> dict:
    if collection.image_id:
        image = {"src": collection.image.url, "alt": collection.image_alt or collection.image.alt, "fit": "cover"}
        if collection.image.file_640:
            image["src640"] = collection.image.url_640
    else:
        image = _fallback_image(collection)
    payload = {
        "id": collection.slug,
        "label": collection.name,
        "description": collection.description,
        "image": image,
        "productCount": getattr(collection, "product_count", None),
    }
    arabic = {k: v for k, v in {"label": collection.name_ar, "description": collection.description_ar}.items() if v}
    if arabic:
        payload["translations"] = {"ar": arabic}
    return payload


def collections_payload(include_empty: bool = False) -> list:
    """
    Boutique : `include_empty=True` — collections visibles, y compris vides (`productCount` = 0). Le front n'affiche
    les vides QUE dans les onglets de l'accueil ; menu, pages collection et plan du site restent limités aux pleines.
    """
    return [collection_payload(c) for c in visible_collections(include_empty)]
