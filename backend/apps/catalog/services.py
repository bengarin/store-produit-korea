"""
Règles métier du catalogue. Toute écriture passe par ici (les vues restent minces).
Chaque modification importante est tracée dans le journal d'audit.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from apps.audit.services import log_action
from apps.core.http import Conflict

from .models import (
    Product,
    ProductCategory,
    ProductImage,
    ProductOption,
    ProductOptionValue,
    Variant,
    VariantOptionValue,
)

MAX_OPTIONS = 3
MAX_VALUES_PER_OPTION = 50
DEFAULT_VARIANT_TITLE = "Par défaut"


# --- Identifiants ---------------------------------------------------------
def unique_slug(text: str, model, *, exclude_pk=None, max_length=120) -> str:
    base = (slugify(text) or "produit")[: max_length - 4].strip("-")
    slug, n = base, 2
    qs = model.objects.exclude(pk=exclude_pk)
    while qs.filter(slug=slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


# --- Conditions de mise en ligne ----------------------------------------
def activation_errors(product: Product) -> list[str]:
    """
    Ce qui manque pour qu'un produit puisse être « Actif » (vérifié côté serveur, toujours).
    Relit TOUJOURS la base : l'objet reçu peut porter des relations préchargées périmées.
    """
    fresh = Product.objects.get(pk=product.pk)
    errors = []
    if not fresh.brand.strip():
        errors.append("La marque est obligatoire.")
    if not fresh.name.strip():
        errors.append("Le nom est obligatoire.")
    if not fresh.summary.strip():
        errors.append("La description est obligatoire.")
    if not ProductCategory.objects.filter(product_id=fresh.pk).exists():
        errors.append("Au moins une catégorie est obligatoire.")
    if not ProductImage.objects.filter(product_id=fresh.pk, in_gallery=True).exists():
        errors.append("Au moins une image dans la galerie est obligatoire.")
    variants = list(Variant.objects.filter(product_id=fresh.pk).prefetch_related("option_values"))
    default = next((v for v in variants if v.is_default), None)
    if default is None:
        errors.append("Une variante par défaut est obligatoire.")
    elif default.price <= 0:
        errors.append("Le prix doit être supérieur à 0.")
    option_count = ProductOption.objects.filter(product_id=fresh.pk).count()
    if option_count:
        combos = set()
        for v in variants:
            values = frozenset(ov.pk for ov in v.option_values.all())
            if len(values) != option_count:
                errors.append(f"La variante « {v.title or v.pk} » doit avoir une valeur pour chaque option.")
            elif values in combos:
                errors.append(f"La variante « {v.title} » est en double.")
            combos.add(values)
    return errors


def ensure_still_valid(product: Product):
    """Après une modification d'un produit ACTIF : refuse (et annule) si la fiche devient incomplète."""
    if Product.objects.filter(pk=product.pk, status=Product.Status.ACTIVE).exists():
        errors = activation_errors(product)
        if errors:
            raise ValidationError({"status": errors}, code="activation_requirements")


@transaction.atomic
def change_status(product: Product, new_status: str, *, user=None, request=None) -> Product:
    product = Product.objects.select_for_update().get(pk=product.pk)
    old = product.status
    if new_status not in Product.Status.values:
        raise ValidationError({"status": ["Statut inconnu."]})
    if new_status == Product.Status.ACTIVE:
        errors = activation_errors(product)
        if errors:
            raise ValidationError({"status": errors}, code="activation_requirements")
        product.published_at = product.published_at or timezone.now()
    product.status = new_status
    product.save(update_fields=["status", "published_at", "updated_at"])
    if old != new_status:
        log_action("product.status", actor=user, target=product, changes={"status": [old, new_status]}, request=request)
    return product


# --- Suppression ----------------------------------------------------------
def external_references(instance) -> int:
    """
    Nombre de lignes HORS catalogue qui pointent vers cet objet (ex. lignes de commande en phase 2).
    Générique : toute future table qui référence un produit ou une variante bloquera sa suppression.
    """
    total = 0
    for rel in instance._meta.related_objects:
        if rel.related_model._meta.app_label in {"catalog", "media_library"}:
            continue
        if rel.one_to_many or rel.one_to_one:
            total += rel.related_model._base_manager.filter(**{rel.field.name: instance}).count()
    return total


@transaction.atomic
def delete_product(product: Product, *, user=None, request=None):
    if product.status == Product.Status.ACTIVE:
        raise Conflict("Un produit actif ne peut pas être supprimé : archivez-le d'abord.", "product_active")
    used = external_references(product) + sum(external_references(v) for v in product.variants.all())
    if used:
        raise Conflict(
            "Ce produit a déjà été utilisé (commandes) : il ne peut pas être supprimé. Archivez-le.",
            "product_in_use",
        )
    snapshot = {"slug": product.slug, "name": product.public_name, "status": product.status}
    product_id = product.pk
    Product.objects.filter(pk=product_id).update(hover_image=None, scene_image=None)
    product.delete()
    log_action(
        "product.delete",
        actor=user,
        target_type="catalog.product",
        target_id=product_id,
        changes=snapshot,
        request=request,
    )


# --- Options et variantes ---------------------------------------------
def _clean_list(values, label):
    cleaned = [str(v).strip() for v in values]
    if any(not v for v in cleaned):
        raise ValidationError({label: ["Les valeurs vides ne sont pas autorisées."]})
    if len({v.lower() for v in cleaned}) != len(cleaned):
        raise ValidationError({label: ["Valeurs en double."]})
    return cleaned


@transaction.atomic
def set_options(product: Product, options: list[dict], *, user=None, request=None):
    """Remplace la liste des options : [{"name": "Contenance", "values": ["50 ml", "100 ml"]}]."""
    product = Product.objects.select_for_update().get(pk=product.pk)
    if len(options) > MAX_OPTIONS:
        raise ValidationError({"options": [f"{MAX_OPTIONS} options maximum."]})
    names = _clean_list([o.get("name", "") for o in options], "options")
    wanted = {}
    for name, option in zip(names, options, strict=True):
        values = _clean_list(option.get("values") or [], "options")
        if not values or len(values) > MAX_VALUES_PER_OPTION:
            raise ValidationError({"options": [f"« {name} » : entre 1 et {MAX_VALUES_PER_OPTION} valeurs."]})
        wanted[name] = values

    for existing in product.options.prefetch_related("values"):
        keep = wanted.get(existing.name)
        removed = [v for v in existing.values.all() if keep is None or v.value not in keep]
        used = VariantOptionValue.objects.filter(option_value__in=removed)
        if used.exists():
            raise Conflict(
                f"Des variantes utilisent encore « {existing.name} » : modifiez-les ou supprimez-les d'abord.",
                "option_in_use",
            )
        for value in removed:
            value.delete()
        if keep is None:
            existing.delete()

    for position, (name, values) in enumerate(wanted.items()):
        option, _ = ProductOption.objects.update_or_create(product=product, name=name, defaults={"position": position})
        for vpos, value in enumerate(values):
            ProductOptionValue.objects.update_or_create(option=option, value=value, defaults={"position": vpos})

    log_action("product.options", actor=user, target=product, changes={"options": wanted}, request=request)
    ensure_still_valid(product)
    return product


def _resolve_option_values(product: Product, mapping: dict) -> list[ProductOptionValue]:
    options = {o.name: o for o in product.options.prefetch_related("values")}
    mapping = mapping or {}
    unknown = set(mapping) - set(options)
    if unknown:
        raise ValidationError({"optionValues": [f"Option inconnue : {', '.join(sorted(unknown))}."]})
    if options and set(mapping) != set(options):
        raise ValidationError({"optionValues": ["Choisissez une valeur pour chaque option du produit."]})
    resolved = []
    for name, value in mapping.items():
        match = next((v for v in options[name].values.all() if v.value == str(value).strip()), None)
        if match is None:
            raise ValidationError({"optionValues": [f"« {value} » n'est pas une valeur de « {name} »."]})
        resolved.append(match)
    return resolved


@transaction.atomic
def save_variant(product: Product, data: dict, *, variant: Variant | None = None, user=None, request=None):
    product = Product.objects.select_for_update().get(pk=product.pk)
    option_map = data.pop("option_values", None)
    creating = variant is None
    if creating:
        variant = Variant(product=product, position=product.variants.count())
    before = {k: getattr(variant, k) for k in data} if not creating else {}
    for key, value in data.items():
        setattr(variant, key, value)

    values = None
    if option_map is not None or creating:
        values = _resolve_option_values(product, option_map or {})
        combo = {v.pk for v in values}
        for other in product.variants.exclude(pk=variant.pk).prefetch_related("option_values"):
            if combo and {v.pk for v in other.option_values.all()} == combo:
                raise ValidationError({"optionValues": ["Une variante avec ces valeurs existe déjà."]})
        variant.title = " / ".join(v.value for v in values) if values else DEFAULT_VARIANT_TITLE

    if not product.variants.exclude(pk=variant.pk).filter(is_default=True).exists():
        variant.is_default = True
    variant.save()
    if variant.is_default:
        product.variants.exclude(pk=variant.pk).filter(is_default=True).update(is_default=False)
    if values is not None:
        VariantOptionValue.objects.filter(variant=variant).delete()
        VariantOptionValue.objects.bulk_create([VariantOptionValue(variant=variant, option_value=v) for v in values])

    changes = (
        {k: [_plain(before.get(k)), _plain(getattr(variant, k))] for k in data}
        if not creating
        else {k: _plain(v) for k, v in data.items()}
    )
    log_action(
        "variant.create" if creating else "variant.update",
        actor=user,
        target=variant,
        changes={"product": product.slug, **changes},
        request=request,
    )
    ensure_still_valid(product)
    return variant


@transaction.atomic
def delete_variant(variant: Variant, *, user=None, request=None):
    product = Product.objects.select_for_update().get(pk=variant.product_id)
    if product.variants.count() <= 1:
        raise Conflict("Un produit doit garder au moins une variante.", "last_variant")
    if external_references(variant):
        raise Conflict("Cette variante a déjà été commandée : elle ne peut pas être supprimée.", "variant_in_use")
    was_default = variant.is_default
    variant_id, title = variant.pk, variant.title
    variant.delete()
    if was_default:
        first = product.variants.order_by("position", "id").first()
        first.is_default = True
        first.save(update_fields=["is_default", "updated_at"])
    log_action(
        "variant.delete",
        actor=user,
        target_type="catalog.variant",
        target_id=variant_id,
        changes={"product": product.slug, "title": title},
        request=request,
    )
    ensure_still_valid(product)


# --- Images -----------------------------------------------------------
@transaction.atomic
def reorder_images(product: Product, ids: list[int], *, user=None, request=None):
    gallery = list(product.images.filter(in_gallery=True).values_list("pk", flat=True))
    if sorted(ids) != sorted(gallery):
        raise ValidationError({"ids": ["La liste doit contenir exactement les images de la galerie."]})
    for position, pk in enumerate(ids):
        ProductImage.objects.filter(pk=pk).update(position=position)
    log_action("product.images_reorder", actor=user, target=product, changes={"order": ids}, request=request)


@transaction.atomic
def delete_image(image: ProductImage, *, user=None, request=None):
    product = image.product
    Product.objects.filter(pk=product.pk, hover_image=image).update(hover_image=None)
    Product.objects.filter(pk=product.pk, scene_image=image).update(scene_image=None)
    image_id = image.pk
    image.delete()
    log_action("product.image_delete", actor=user, target=product, changes={"imageId": image_id}, request=request)
    product.refresh_from_db()
    ensure_still_valid(product)


def _plain(value):
    if isinstance(value, Decimal):
        return str(value)
    return value
