"""
Format PUBLIC d'un produit : identique à celui du catalogue local du front
(src/data/local + src/services/productService.js → normalizeProduct) — voir docs/BACKEND.md.

- `id` = slug (le panier, les favoris et les liens du front utilisent cet identifiant)
- le coût, le stock exact et les brouillons ne sont JAMAIS exposés
"""

from decimal import Decimal

from django.db.models import Prefetch

from .models import Category, Product, ProductCategory, ProductImage, Variant


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


def public_products_queryset(statuses=(Product.Status.ACTIVE,)):
    """Produits au format public. `statuses` élargi uniquement pour l'aperçu de l'administration."""
    return (
        Product.objects.filter(status__in=statuses)
        .select_related("hover_image__media", "scene_image__media", "og_image")
        .prefetch_related(
            Prefetch(
                "category_links",
                queryset=ProductCategory.objects.filter(category__is_active=True).select_related("category"),
            ),
            "highlights",
            Prefetch("images", queryset=ProductImage.objects.filter(in_gallery=True).select_related("media")),
            Prefetch("variants", queryset=Variant.objects.prefetch_related("option_values__option")),
        )
    )


def product_payload(product: Product) -> dict:
    gallery = [image_payload(i) for i in product.images.all()]
    main = gallery[0] if gallery else None
    scene = image_payload(product.scene_image) if product.scene_image_id else main
    hover = image_payload(product.hover_image, product.hover_image_position) if product.hover_image_id else None
    variants = list(product.variants.all())
    default = next((v for v in variants if v.is_default), variants[0] if variants else None)
    return {
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
        "stock": None,  # quantité exacte volontairement non publiée
        "inStock": any(v.is_available for v in variants),
        "cardImage": main,
        "mainImage": main,
        "galleryImages": gallery,
        "image": scene,
        "sceneImage": scene,
        "hoverImage": hover,
        "variants": [
            {
                "id": v.pk,
                "title": v.title,
                "price": number(v.price),
                "compareAtPrice": number(v.compare_at_price),
                "available": v.is_available,
                "isDefault": v.is_default,
                "options": {ov.option.name: ov.value for ov in v.option_values.all()},
            }
            for v in variants
        ],
        "seo": {
            "title": product.seo_title or product.public_name,
            "description": product.seo_description or product.short_description or product.summary[:160],
            "image": product.og_image.url if product.og_image_id else (main["src"] if main else None),
        },
    }


def category_payload(category: Category) -> dict:
    return {"id": category.slug, "label": category.name}
