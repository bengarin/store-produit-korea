from django.db import transaction
from django.db.models import Count, Prefetch, ProtectedError, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.core.http import Conflict

from . import public, services
from .models import Category, Product, ProductCategory, ProductImage, Variant
from .permissions import CATALOG_PERMISSION
from .serializers import (
    CategorySerializer,
    ProductImageSerializer,
    ProductListSerializer,
    ProductSerializer,
    VariantSerializer,
)


# ============================== API PUBLIQUE ==============================
class PublicView(APIView):
    """Lecture seule, sans session ni CSRF ; limitée par le débit « anon »."""

    permission_classes = [AllowAny]
    authentication_classes = []


class PublicProductListView(PublicView):
    def get(self, request):
        return Response({"items": [public.product_payload(p) for p in public.public_products_queryset()]})


class PublicProductDetailView(PublicView):
    def get(self, request, slug):
        product = get_object_or_404(public.public_products_queryset(), slug=slug)
        return Response(public.product_payload(product))


class PublicCategoryListView(PublicView):
    def get(self, request):
        return Response({"items": [public.category_payload(c) for c in Category.objects.filter(is_active=True)]})


# =============================== API ADMIN ================================
class CategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = [CATALOG_PERMISSION]
    pagination_class = None  # quelques catégories : liste complète

    def get_queryset(self):
        return Category.objects.annotate(productCount=Count("product_links"))

    def perform_create(self, serializer):
        category = serializer.save()
        log_action(
            "category.create",
            actor=self.request.user,
            target=category,
            changes={"slug": category.slug, "name": category.name},
            request=self.request,
        )


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = [CATALOG_PERMISSION]
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self):
        return Category.objects.annotate(productCount=Count("product_links"))

    def perform_update(self, serializer):
        before = {k: getattr(serializer.instance, k) for k in serializer.validated_data}
        category = serializer.save()
        changes = {k: [str(v), str(getattr(category, k))] for k, v in before.items() if v != getattr(category, k)}
        log_action("category.update", actor=self.request.user, target=category, changes=changes, request=self.request)

    def perform_destroy(self, category):
        try:
            with transaction.atomic():
                snapshot = {"slug": category.slug, "name": category.name}
                pk = category.pk
                category.delete()
                log_action(
                    "category.delete",
                    actor=self.request.user,
                    target_type="catalog.category",
                    target_id=pk,
                    changes=snapshot,
                    request=self.request,
                )
        except ProtectedError as exc:
            raise Conflict("Cette catégorie contient des produits : retirez-les d'abord.", "category_in_use") from exc


class ReorderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False, max_length=500)


class CategoryReorderView(APIView):
    permission_classes = [CATALOG_PERMISSION]

    @transaction.atomic
    def post(self, request):
        data = ReorderSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        ids = data.validated_data["ids"]
        if sorted(ids) != sorted(Category.objects.values_list("pk", flat=True)):
            raise serializers.ValidationError({"ids": ["La liste doit contenir toutes les catégories."]})
        for position, pk in enumerate(ids):
            Category.objects.filter(pk=pk).update(position=position)
        log_action("category.reorder", actor=request.user, changes={"order": ids}, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


def admin_products_queryset():
    return Product.objects.prefetch_related(
        "variants",
        Prefetch("images", queryset=ProductImage.objects.select_related("media")),
        Prefetch("category_links", queryset=ProductCategory.objects.select_related("category")),
        "highlights",
    )


class ProductListCreateView(generics.ListCreateAPIView):
    """Filtres : ?status=active|draft|archived · ?category=<slug> · ?search=texte · ?ordering=position|-updated_at"""

    permission_classes = [CATALOG_PERMISSION]
    ORDERINGS = {"position", "-position", "updated_at", "-updated_at", "name", "-name"}

    def get_serializer_class(self):
        return ProductListSerializer if self.request.method == "GET" else ProductSerializer

    def get_queryset(self):
        qs = admin_products_queryset()
        params = self.request.query_params
        if params.get("status") in Product.Status.values:
            qs = qs.filter(status=params["status"])
        if params.get("category"):
            qs = qs.filter(category_links__category__slug=params["category"])
        term = params.get("search", "").strip()
        if term:
            qs = qs.filter(
                Q(name__icontains=term)
                | Q(brand__icontains=term)
                | Q(display_name__icontains=term)
                | Q(slug__icontains=term)
                | Q(variants__sku__iexact=term)
            ).distinct()
        ordering = params.get("ordering")
        return qs.order_by(ordering, "id") if ordering in self.ORDERINGS else qs

    def create(self, request, *args, **kwargs):
        serializer = ProductSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(
            ProductSerializer(product, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED
        )


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = [CATALOG_PERMISSION]
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self):
        return admin_products_queryset()

    def perform_destroy(self, product):
        services.delete_product(product, user=self.request.user, request=self.request)


class StatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Product.Status.choices)


class ProductStatusView(APIView):
    """POST {"status": "active"} — l'activation vérifie les conditions côté serveur."""

    permission_classes = [CATALOG_PERMISSION]

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        data = StatusSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        product = services.change_status(product, data.validated_data["status"], user=request.user, request=request)
        return Response(ProductSerializer(product, context={"request": request}).data)


class OptionInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    values = serializers.ListField(child=serializers.CharField(max_length=50), allow_empty=False, max_length=50)


class ProductOptionsView(APIView):
    """PUT [{"name": "Contenance", "values": ["50 ml", "100 ml"]}] — remplace les options."""

    permission_classes = [CATALOG_PERMISSION]

    def put(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        data = OptionInputSerializer(data=request.data, many=True)
        data.is_valid(raise_exception=True)
        services.set_options(product, data.validated_data, user=request.user, request=request)
        return Response(ProductSerializer(product, context={"request": request}).data["options"])


class VariantListCreateView(APIView):
    permission_classes = [CATALOG_PERMISSION]

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        qs = product.variants.prefetch_related("option_values__option")
        return Response({"items": VariantSerializer(qs, many=True, context={"request": request}).data})

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = VariantSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        variant = services.save_variant(product, dict(serializer.validated_data), user=request.user, request=request)
        return Response(VariantSerializer(variant, context={"request": request}).data, status=status.HTTP_201_CREATED)


class VariantDetailView(APIView):
    permission_classes = [CATALOG_PERMISSION]

    def get_object(self, pk):
        return get_object_or_404(Variant.objects.prefetch_related("option_values__option"), pk=pk)

    def get(self, request, pk):
        return Response(VariantSerializer(self.get_object(pk), context={"request": request}).data)

    def patch(self, request, pk):
        variant = self.get_object(pk)
        serializer = VariantSerializer(variant, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        variant = services.save_variant(
            variant.product, dict(serializer.validated_data), variant=variant, user=request.user, request=request
        )
        variant = self.get_object(variant.pk)
        return Response(VariantSerializer(variant, context={"request": request}).data)

    def delete(self, request, pk):
        services.delete_variant(self.get_object(pk), user=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductImageListCreateView(APIView):
    """GET : images du produit · POST {"mediaId", "alt", "fit", "kind", "focalPosition", "inGallery"}."""

    permission_classes = [CATALOG_PERMISSION]

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        return Response({"items": ProductImageSerializer(product.images.select_related("media"), many=True).data})

    @transaction.atomic
    def post(self, request, pk):
        product = get_object_or_404(Product.objects.select_for_update(), pk=pk)
        serializer = ProductImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        last = product.images.order_by("-position").values_list("position", flat=True).first()
        image = serializer.save(product=product, position=0 if last is None else last + 1)
        log_action(
            "product.image_add",
            actor=request.user,
            target=product,
            changes={"imageId": image.pk, "mediaId": image.media_id},
            request=request,
        )
        return Response(ProductImageSerializer(image).data, status=status.HTTP_201_CREATED)


class ProductImageReorderView(APIView):
    permission_classes = [CATALOG_PERMISSION]

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        data = ReorderSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.reorder_images(product, data.validated_data["ids"], user=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductImageDetailView(APIView):
    permission_classes = [CATALOG_PERMISSION]

    def get_object(self, pk):
        return get_object_or_404(ProductImage.objects.select_related("media", "product"), pk=pk)

    @transaction.atomic
    def patch(self, request, pk):
        image = self.get_object(pk)
        serializer = ProductImageSerializer(image, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        image = serializer.save()
        log_action(
            "product.image_update",
            actor=request.user,
            target=image.product,
            changes={"imageId": image.pk, **request.data},
            request=request,
        )
        services.ensure_still_valid(image.product)
        return Response(ProductImageSerializer(image).data)

    def delete(self, request, pk):
        services.delete_image(self.get_object(pk), user=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)
