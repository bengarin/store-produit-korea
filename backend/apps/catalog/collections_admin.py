"""
Admin → Collections : « Soins naturels », « Beauté chinoise »… Une collection regroupe des produits EXISTANTS :
un produit peut être dans une ou plusieurs collections, sans copie de sa fiche, de son stock ni de son prix.

- Collections (textes FR / AR, image, ordre, visibilité, règles) : Propriétaire et Admin.
- Produits d'une collection : Propriétaire, Admin, Éditeur (comme la fiche produit). Seuls ces liens changent.
- Règles d'entrée vérifiées par le serveur : pays de fabrication exigé, liste d'ingrédients exigée. Un produit
  qui ne les respecte pas est refusé, avec la raison (rien n'est affirmé sans information vérifiée).
"""

from django.db import transaction
from django.db.models import Count, Q
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.media_library.models import MediaAsset

from .filters_admin import _clean, _next_position, _reorder
from .models import ORIGIN_COUNTRIES, Collection, Product
from .permissions import CATALOG_PERMISSION, CATEGORY_PERMISSION
from .services import unique_slug


class CollectionSerializer(serializers.ModelSerializer):
    nameAr = serializers.CharField(source="name_ar", max_length=80, required=False, allow_blank=True)
    descriptionAr = serializers.CharField(source="description_ar", max_length=300, required=False, allow_blank=True)
    imageId = serializers.PrimaryKeyRelatedField(
        source="image", queryset=MediaAsset.objects.all(), allow_null=True, required=False
    )
    image = serializers.SerializerMethodField()
    imageAlt = serializers.CharField(source="image_alt", max_length=255, required=False, allow_blank=True)
    isActive = serializers.BooleanField(source="is_active", required=False)
    requiredOrigin = serializers.ChoiceField(
        source="required_origin", choices=ORIGIN_COUNTRIES, required=False, allow_blank=True
    )
    requireIngredients = serializers.BooleanField(source="require_ingredients", required=False)
    productCount = serializers.IntegerField(read_only=True, default=0)
    activeCount = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Collection
        fields = [
            "id", "slug", "name", "nameAr", "description", "descriptionAr", "imageId", "image", "imageAlt",
            "position", "isActive", "requiredOrigin", "requireIngredients", "productCount", "activeCount",
        ]  # fmt: skip
        read_only_fields = ["slug", "position"]

    def get_image(self, collection):
        if not collection.image_id:
            return None
        media = collection.image
        return {"id": media.pk, "src": media.url_640 if media.file_640 else media.url, "alt": media.alt}

    def validate_name(self, value):
        value = _clean(value)
        if not value:
            raise serializers.ValidationError("Le nom est obligatoire.")
        return value

    def validate_nameAr(self, value):
        return _clean(value)

    def validate_description(self, value):
        return _clean(value)

    def validate_descriptionAr(self, value):
        return _clean(value)

    def validate_imageAlt(self, value):
        return _clean(value)

    def validate(self, attrs):
        """Règles durcies sur une collection déjà remplie : refusé si des produits ne les respectent plus."""
        current = self.instance
        if current is None or not ({"required_origin", "require_ingredients"} & attrs.keys()):
            return attrs
        probe = Collection(
            name=attrs.get("name", current.name),
            required_origin=attrs.get("required_origin", current.required_origin),
            require_ingredients=attrs.get("require_ingredients", current.require_ingredients),
        )
        bad = [
            p.public_name
            for p in current.products.all()
            if probe.entry_errors(origin=p.origin_country, ingredients=p.ingredients)
        ]
        if bad:
            raise serializers.ValidationError(
                {
                    "requiredOrigin": [
                        f"Ces produits ne respectent pas la règle : {', '.join(bad)}. Retirez-les d'abord."
                    ]
                }
            )
        return attrs


def collections_queryset():
    return (
        Collection.objects.select_related("image")
        .annotate(
            productCount=Count("products", distinct=True),
            activeCount=Count("products", filter=Q(products__status=Product.Status.ACTIVE), distinct=True),
        )
        .order_by("position", "id")
    )  # l'ordre du modèle est ignoré par Django dans une requête avec Count


class CollectionListCreateView(generics.ListCreateAPIView):
    """GET : toutes les collections (visibles ou non) · POST : nouvelle collection."""

    serializer_class = CollectionSerializer
    permission_classes = [CATEGORY_PERMISSION]
    pagination_class = None

    def get_queryset(self):
        return collections_queryset()

    def perform_create(self, serializer):
        name = serializer.validated_data["name"]
        collection = serializer.save(
            slug=unique_slug(name, Collection, max_length=80), position=_next_position(Collection.objects)
        )
        log_action(
            "collection.create",
            actor=self.request.user,
            target=collection,
            changes={"name": name},
            request=self.request,
        )


class CollectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """PATCH : textes, image, visibilité, règles · DELETE : supprime la collection (les produits restent intacts)."""

    serializer_class = CollectionSerializer
    permission_classes = [CATEGORY_PERMISSION]
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self):
        return collections_queryset()

    def perform_update(self, serializer):
        collection = serializer.save()
        changes = {k: getattr(v, "pk", v) for k, v in serializer.validated_data.items()}
        log_action(
            "collection.update", actor=self.request.user, target=collection, changes=changes, request=self.request
        )

    def perform_destroy(self, instance):
        log_action(
            "collection.delete", actor=self.request.user, target=instance,
            changes={"name": instance.name, "products": instance.products.count()}, request=self.request,
        )  # fmt: skip
        instance.delete()


class CollectionReorderView(APIView):
    permission_classes = [CATEGORY_PERMISSION]

    def post(self, request):
        return _reorder(request, Collection.objects.all(), "collection.reorder")


class CollectionProductsSerializer(serializers.Serializer):
    productIds = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=True, max_length=2000)


def _candidate(collection: Collection, product: Product, selected: set) -> dict:
    reasons = collection.entry_errors(origin=product.origin_country, ingredients=product.ingredients)
    return {
        "id": product.pk,
        "name": product.public_name,
        "brand": product.brand,
        "status": product.status,
        "originCountry": product.origin_country,
        "hasIngredients": bool([i for i in product.ingredients or [] if str(i).strip()]),
        "selected": product.pk in selected,
        "eligible": not reasons,
        "reasons": reasons,
    }


class CollectionProductsView(APIView):
    """
    GET : produits de la collection + tous les produits avec leur éligibilité (et la raison d'un refus).
    PUT {productIds} : remplace la liste. Seuls les liens de CETTE collection changent : fiches, prix, stocks,
    statuts et autres collections des produits ne sont jamais touchés.
    """

    permission_classes = [CATALOG_PERMISSION]

    def get(self, request, pk):
        collection = generics.get_object_or_404(Collection, pk=pk)
        selected = set(collection.products.values_list("pk", flat=True))
        products = Product.objects.exclude(status=Product.Status.ARCHIVED).order_by("position", "id")
        archived_selected = Product.objects.filter(pk__in=selected, status=Product.Status.ARCHIVED)
        rows = [_candidate(collection, p, selected) for p in [*products, *archived_selected]]
        return Response({"productIds": sorted(selected), "products": rows})

    @transaction.atomic
    def put(self, request, pk):
        collection = generics.get_object_or_404(Collection.objects.select_for_update(), pk=pk)
        data = CollectionProductsSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        wanted = set(data.validated_data["productIds"])
        products = {p.pk: p for p in Product.objects.filter(pk__in=wanted)}
        unknown = wanted - products.keys()
        if unknown:
            raise serializers.ValidationError({"productIds": [f"Produit introuvable : {sorted(unknown)}."]})
        current = set(collection.products.values_list("pk", flat=True))
        added, removed = wanted - current, current - wanted
        errors = [
            f"{products[pk].public_name} — {reason}"
            for pk in sorted(added)
            for reason in collection.entry_errors(
                origin=products[pk].origin_country, ingredients=products[pk].ingredients
            )
        ]
        if errors:
            raise serializers.ValidationError({"productIds": errors})
        collection.products.remove(*removed)
        collection.products.add(*added)
        if added or removed:
            log_action(
                "collection.products", actor=request.user, target=collection,
                changes={"added": sorted(added), "removed": sorted(removed)}, request=request,
            )  # fmt: skip
        return Response({"productIds": sorted(wanted)}, status=status.HTTP_200_OK)
