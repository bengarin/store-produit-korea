"""
Sérialiseurs de l'API ADMIN (champs en camelCase, comme le front).
Le coût n'est visible que des rôles COST_VIEW et modifiable que par COST_EDIT.
"""

from django.db import transaction
from rest_framework import serializers

from apps.audit.services import log_action
from apps.core.html import sanitize_html
from apps.media_library.models import MediaAsset

from . import services
from .models import FOCAL_POSITION, Category, Product, ProductCategory, ProductHighlight, ProductImage, Variant
from .permissions import COST_EDIT, COST_VIEW

MAX_LIST_ITEMS = 30
MAX_ITEM_LENGTH = 500


def _role(context):
    request = context.get("request")
    return getattr(getattr(request, "user", None), "role", None)


class TextListField(serializers.ListField):
    """Liste de phrases (ingrédients, bienfaits, étapes)."""

    def __init__(self, **kwargs):
        super().__init__(
            child=serializers.CharField(max_length=MAX_ITEM_LENGTH, allow_blank=False),
            max_length=MAX_LIST_ITEMS,
            required=False,
            **kwargs,
        )


# --- Catégories -----------------------------------------------------------
class CategorySerializer(serializers.ModelSerializer):
    parentId = serializers.PrimaryKeyRelatedField(
        source="parent", queryset=Category.objects.all(), allow_null=True, required=False
    )
    isActive = serializers.BooleanField(source="is_active", required=False)
    seoTitle = serializers.CharField(source="seo_title", max_length=70, required=False, allow_blank=True)
    seoDescription = serializers.CharField(source="seo_description", max_length=160, required=False, allow_blank=True)
    productCount = serializers.IntegerField(read_only=True, default=0)
    slug = serializers.SlugField(max_length=80, required=False)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "slug",
            "name",
            "parentId",
            "position",
            "isActive",
            "description",
            "seoTitle",
            "seoDescription",
            "productCount",
            "createdAt",
            "updatedAt",
        ]

    def validate_slug(self, value):
        qs = Category.objects.filter(slug=value).exclude(pk=getattr(self.instance, "pk", None))
        if qs.exists():
            raise serializers.ValidationError("Cet identifiant est déjà utilisé.")
        return value

    def validate_parentId(self, parent):
        node = parent
        while node is not None:
            if self.instance is not None and node.pk == self.instance.pk:
                raise serializers.ValidationError("Une catégorie ne peut pas être sa propre parente.")
            node = node.parent
        return parent

    def create(self, validated_data):
        validated_data.setdefault("slug", services.unique_slug(validated_data["name"], Category, max_length=80))
        return super().create(validated_data)


# --- Images ---------------------------------------------------------------
class ProductImageSerializer(serializers.ModelSerializer):
    mediaId = serializers.PrimaryKeyRelatedField(source="media", queryset=MediaAsset.objects.all())
    url = serializers.CharField(source="media.url", read_only=True)
    url640 = serializers.CharField(source="media.url_640", read_only=True)
    focalPosition = serializers.CharField(
        source="focal_position", required=False, allow_blank=True, max_length=20, validators=[FOCAL_POSITION]
    )
    inGallery = serializers.BooleanField(source="in_gallery", required=False)

    class Meta:
        model = ProductImage
        fields = ["id", "mediaId", "url", "url640", "alt", "kind", "fit", "focalPosition", "position", "inGallery"]
        read_only_fields = ["position"]

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None and not isinstance(self.instance, list):
            fields["mediaId"].read_only = True  # on remplace une image en en ajoutant une autre
        return fields


# --- Variantes ------------------------------------------------------------
class VariantSerializer(serializers.ModelSerializer):
    compareAtPrice = serializers.DecimalField(
        source="compare_at_price", max_digits=10, decimal_places=2, allow_null=True, required=False, min_value=0
    )
    cost = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True, required=False, min_value=0)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    # Lecture seule : le stock change UNIQUEMENT par un mouvement de stock (POST /admin/inventory/adjust).
    stockQuantity = serializers.IntegerField(source="stock_quantity", read_only=True, allow_null=True)
    trackInventory = serializers.BooleanField(source="track_inventory", required=False)
    allowBackorder = serializers.BooleanField(source="allow_backorder", required=False)
    lowStockThreshold = serializers.IntegerField(source="low_stock_threshold", required=False, min_value=0)
    weightGrams = serializers.IntegerField(source="weight_grams", required=False, allow_null=True, min_value=0)
    isDefault = serializers.BooleanField(source="is_default", required=False)
    optionValues = serializers.DictField(
        source="option_values", child=serializers.CharField(max_length=50), required=False, write_only=True
    )
    options = serializers.SerializerMethodField()
    sku = serializers.CharField(max_length=64, required=False, allow_blank=True, allow_null=True)
    barcode = serializers.CharField(max_length=64, required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Variant
        fields = [
            "id",
            "title",
            "sku",
            "barcode",
            "price",
            "compareAtPrice",
            "cost",
            "stockQuantity",
            "trackInventory",
            "allowBackorder",
            "lowStockThreshold",
            "weightGrams",
            "position",
            "isDefault",
            "optionValues",
            "options",
        ]
        read_only_fields = ["title", "position"]

    def get_options(self, variant):
        return {v.option.name: v.value for v in variant.option_values.all()}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if _role(self.context) not in COST_VIEW:
            data.pop("cost", None)  # jamais envoyé aux rôles qui n'ont pas à le voir
        return data

    def validate_cost(self, value):
        if _role(self.context) not in COST_EDIT:
            raise serializers.ValidationError("Vous n'avez pas le droit de modifier le coût.")
        return value

    def _unique(self, field, value):
        value = (value or "").strip() or None
        if value and Variant.objects.filter(**{field: value}).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Déjà utilisé par une autre variante.")
        return value

    def validate_sku(self, value):
        return self._unique("sku", value)

    def validate_barcode(self, value):
        return self._unique("barcode", value)

    def validate(self, attrs):
        price = attrs.get("price", getattr(self.instance, "price", None))
        compare = attrs.get("compare_at_price", getattr(self.instance, "compare_at_price", None))
        if compare is not None and price is not None and compare <= price:
            raise serializers.ValidationError({"compareAtPrice": ["Le prix barré doit être supérieur au prix."]})
        stock = getattr(self.instance, "stock_quantity", None)
        backorder = attrs.get("allow_backorder", getattr(self.instance, "allow_backorder", False))
        if stock is not None and stock < 0 and not backorder:
            raise serializers.ValidationError(
                {"allowBackorder": ["Stock négatif : régularisez le stock avant de désactiver la vente sans stock."]}
            )
        return attrs


class DefaultVariantInputSerializer(VariantSerializer):
    """Variante par défaut fournie à la création du produit (prix facultatif en brouillon)."""

    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False, default=0)

    class Meta(VariantSerializer.Meta):
        fields = [f for f in VariantSerializer.Meta.fields if f not in ("optionValues", "isDefault")]


# --- Produits -------------------------------------------------------------
class HighlightSerializer(serializers.Serializer):
    icon = serializers.ChoiceField(choices=ProductHighlight.Icon.choices)
    label = serializers.CharField(max_length=60)


class ProductListSerializer(serializers.ModelSerializer):
    displayName = serializers.CharField(source="public_name")
    price = serializers.SerializerMethodField()
    totalStock = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    variantCount = serializers.SerializerMethodField()
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = Product
        fields = [
            "id",
            "slug",
            "displayName",
            "brand",
            "status",
            "position",
            "price",
            "totalStock",
            "variantCount",
            "image",
            "categories",
            "updatedAt",
        ]

    def _variants(self, product):
        return list(product.variants.all())

    def get_price(self, product):
        default = next((v for v in self._variants(product) if v.is_default), None)
        return default.price if default else None

    def get_totalStock(self, product):
        """Somme des stocks connus ; None si au moins une variante suivie n'a pas de stock renseigné."""
        tracked = [v for v in self._variants(product) if v.track_inventory]
        if any(v.stock_quantity is None for v in tracked):
            return None
        return sum(v.stock_quantity for v in tracked)

    def get_variantCount(self, product):
        return len(self._variants(product))

    def get_image(self, product):
        first = next((i for i in product.images.all() if i.in_gallery), None)
        return first.media.url if first else None

    def get_categories(self, product):
        return [link.category.slug for link in product.category_links.all()]


class ProductSerializer(serializers.ModelSerializer):
    displayName = serializers.CharField(source="display_name", max_length=255, required=False, allow_blank=True)
    cardLine = serializers.CharField(source="short_description", max_length=160, required=False, allow_blank=True)
    descriptionHtml = serializers.CharField(
        source="description_html", required=False, allow_blank=True, max_length=20000
    )
    ingredients = TextListField()
    benefits = TextListField()
    usage = TextListField(source="usage_steps")
    skinTypes = serializers.CharField(source="skin_types", max_length=255, required=False, allow_blank=True)
    categoryIds = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), many=True, required=False, write_only=True
    )
    categories = serializers.SerializerMethodField()
    highlights = HighlightSerializer(many=True, required=False)
    hoverImageId = serializers.PrimaryKeyRelatedField(
        source="hover_image", queryset=ProductImage.objects.all(), allow_null=True, required=False
    )
    hoverImagePosition = serializers.CharField(
        source="hover_image_position", max_length=20, required=False, allow_blank=True, validators=[FOCAL_POSITION]
    )
    sceneImageId = serializers.PrimaryKeyRelatedField(
        source="scene_image", queryset=ProductImage.objects.all(), allow_null=True, required=False
    )
    seoTitle = serializers.CharField(source="seo_title", max_length=70, required=False, allow_blank=True)
    seoDescription = serializers.CharField(source="seo_description", max_length=160, required=False, allow_blank=True)
    ogImageId = serializers.PrimaryKeyRelatedField(
        source="og_image", queryset=MediaAsset.objects.all(), allow_null=True, required=False
    )
    slug = serializers.SlugField(max_length=120, required=False)
    variant = DefaultVariantInputSerializer(required=False, write_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = serializers.SerializerMethodField()
    options = serializers.SerializerMethodField()
    activationErrors = serializers.SerializerMethodField()
    publishedAt = serializers.DateTimeField(source="published_at", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "slug",
            "position",
            "status",
            "brand",
            "name",
            "displayName",
            "cardLine",
            "summary",
            "descriptionHtml",
            "ingredients",
            "benefits",
            "usage",
            "skinTypes",
            "categoryIds",
            "categories",
            "highlights",
            "images",
            "hoverImageId",
            "hoverImagePosition",
            "sceneImageId",
            "options",
            "variants",
            "variant",
            "seoTitle",
            "seoDescription",
            "ogImageId",
            "activationErrors",
            "publishedAt",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = ["status"]  # le statut change via POST /products/{id}/status

    # Lecture -----------------------------------------------------------
    def get_categories(self, product):
        return [
            {"id": link.category_id, "slug": link.category.slug, "name": link.category.name}
            for link in product.category_links.select_related("category")
        ]

    def get_variants(self, product):
        qs = product.variants.prefetch_related("option_values__option")
        return VariantSerializer(qs, many=True, context=self.context).data

    def get_options(self, product):
        return [
            {"id": o.pk, "name": o.name, "values": [v.value for v in o.values.all()]}
            for o in product.options.prefetch_related("values")
        ]

    def get_activationErrors(self, product):
        return services.activation_errors(product)

    # Validation --------------------------------------------------------
    def validate_slug(self, value):
        if Product.objects.filter(slug=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Cet identifiant est déjà utilisé.")
        return value

    def validate_descriptionHtml(self, value):
        return sanitize_html(value)

    def validate_categoryIds(self, categories):
        if len({c.pk for c in categories}) != len(categories):
            raise serializers.ValidationError("Catégorie en double.")
        return categories

    def validate_highlights(self, value):
        if len(value) > 8:
            raise serializers.ValidationError("8 pictos maximum.")
        return value

    def validate(self, attrs):
        for key, field in (("hover_image", "hoverImageId"), ("scene_image", "sceneImageId")):
            image = attrs.get(key)
            if image is not None and (self.instance is None or image.product_id != self.instance.pk):
                raise serializers.ValidationError({field: ["Cette image n'appartient pas à ce produit."]})
        if self.instance is not None and "variant" in attrs:
            raise serializers.ValidationError({"variant": ["Utilisez l'API des variantes pour modifier les prix."]})
        return attrs

    # Écriture ---------------------------------------------------------
    def _write_relations(self, product, categories, highlights):
        if categories is not None:
            ProductCategory.objects.filter(product=product).delete()
            ProductCategory.objects.bulk_create(
                [ProductCategory(product=product, category=c, position=i) for i, c in enumerate(categories)]
            )
        if highlights is not None:
            product.highlights.all().delete()
            ProductHighlight.objects.bulk_create(
                [ProductHighlight(product=product, position=i, **h) for i, h in enumerate(highlights)]
            )

    @transaction.atomic
    def create(self, validated_data):
        categories = validated_data.pop("categoryIds", None)
        highlights = validated_data.pop("highlights", None)
        variant_data = validated_data.pop("variant", None) or {"price": 0}
        if not validated_data.get("slug"):
            validated_data["slug"] = services.unique_slug(
                validated_data.get("display_name") or f"{validated_data['brand']} {validated_data['name']}", Product
            )
        product = Product.objects.create(status=Product.Status.DRAFT, **validated_data)
        self._write_relations(product, categories, highlights)
        Variant.objects.create(product=product, is_default=True, title=services.DEFAULT_VARIANT_TITLE, **variant_data)
        request = self.context.get("request")
        log_action(
            "product.create",
            actor=getattr(request, "user", None),
            target=product,
            changes={"slug": product.slug, "name": product.public_name},
            request=request,
        )
        return product

    @transaction.atomic
    def update(self, product, validated_data):
        categories = validated_data.pop("categoryIds", None)
        highlights = validated_data.pop("highlights", None)
        before = {k: getattr(product, k) for k in validated_data}
        for key, value in validated_data.items():
            setattr(product, key, value)
        product.save()
        self._write_relations(product, categories, highlights)
        changes = {
            k: [_plain(before[k]), _plain(getattr(product, k))]
            for k in validated_data
            if before[k] != getattr(product, k)
        }
        if categories is not None:
            changes["categories"] = [c.slug for c in categories]
        if highlights is not None:
            changes["highlights"] = highlights
        request = self.context.get("request")
        log_action(
            "product.update", actor=getattr(request, "user", None), target=product, changes=changes, request=request
        )
        services.ensure_still_valid(product)
        return product


def _plain(value):
    if hasattr(value, "pk"):
        return value.pk
    return value if isinstance(value, (str, int, float, bool, list, dict, type(None))) else str(value)
