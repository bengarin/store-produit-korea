"""
Admin → Filtres : groupes de filtres de la page produits, leurs valeurs, et les valeurs cochées sur chaque produit.

- Groupes et valeurs : créer, renommer (FR / AR), réordonner, masquer, supprimer — Propriétaire et Admin.
- Valeurs d'un produit : Propriétaire, Admin, Éditeur (comme la fiche produit). Seuls ces liens changent :
  prix, stocks, statuts et catégories du produit ne sont jamais touchés.
"""

from django.db import transaction
from django.db.models import Count, Prefetch
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_action

from .models import FilterGroup, FilterOption, Product
from .permissions import CATALOG_PERMISSION, CATEGORY_PERMISSION
from .services import unique_slug

FILTERS_PERMISSION = CATEGORY_PERMISSION


def _clean(value: str) -> str:
    value = " ".join((value or "").split())
    if "<" in value or ">" in value:
        raise serializers.ValidationError("Les caractères < et > ne sont pas acceptés.")
    return value


class _Labelled(serializers.ModelSerializer):
    nameAr = serializers.CharField(source="name_ar", max_length=80, required=False, allow_blank=True)
    isActive = serializers.BooleanField(source="is_active", required=False)

    def validate_name(self, value):
        value = _clean(value)
        if not value:
            raise serializers.ValidationError("Le nom est obligatoire.")
        return value

    def validate_nameAr(self, value):
        return _clean(value)


class FilterOptionSerializer(_Labelled):
    productCount = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = FilterOption
        fields = ["id", "slug", "name", "nameAr", "position", "isActive", "productCount"]
        read_only_fields = ["slug", "position"]


class FilterGroupSerializer(_Labelled):
    options = serializers.SerializerMethodField()

    class Meta:
        model = FilterGroup
        fields = ["id", "slug", "name", "nameAr", "position", "isActive", "options"]
        read_only_fields = ["slug", "position"]

    def get_options(self, group):
        return FilterOptionSerializer(group.options.all(), many=True).data


def groups_queryset():
    return FilterGroup.objects.prefetch_related(
        Prefetch("options", queryset=FilterOption.objects.annotate(productCount=Count("products")))
    )


def _next_position(qs):
    last = qs.order_by("-position").values_list("position", flat=True).first()
    return 0 if last is None else last + 1


class FilterGroupListCreateView(generics.ListCreateAPIView):
    """GET : tous les groupes (visibles ou non) avec leurs valeurs · POST : nouveau groupe {name, nameAr}."""

    serializer_class = FilterGroupSerializer
    permission_classes = [FILTERS_PERMISSION]
    pagination_class = None

    def get_queryset(self):
        return groups_queryset()

    def perform_create(self, serializer):
        name = serializer.validated_data["name"]
        group = serializer.save(
            slug=unique_slug(name, FilterGroup, max_length=80), position=_next_position(FilterGroup.objects)
        )
        log_action(
            "filter.group.create", actor=self.request.user, target=group, changes={"name": name}, request=self.request
        )


class FilterGroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    """PATCH {name, nameAr, isActive} · DELETE : supprime le groupe et ses valeurs (les produits restent intacts)."""

    serializer_class = FilterGroupSerializer
    permission_classes = [FILTERS_PERMISSION]
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self):
        return groups_queryset()

    def perform_update(self, serializer):
        group = serializer.save()
        log_action(
            "filter.group.update",
            actor=self.request.user,
            target=group,
            changes=serializer.validated_data,
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_action(
            "filter.group.delete", actor=self.request.user, target=instance,
            changes={"name": instance.name, "options": instance.options.count()}, request=self.request,
        )  # fmt: skip
        instance.delete()


class ReorderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False, max_length=500)


def _reorder(request, qs, action):
    data = ReorderSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    ids = data.validated_data["ids"]
    if sorted(ids) != sorted(qs.values_list("pk", flat=True)):
        raise serializers.ValidationError({"ids": ["La liste doit contenir tous les éléments, une seule fois."]})
    with transaction.atomic():
        for position, pk in enumerate(ids):
            qs.filter(pk=pk).update(position=position)
    log_action(action, actor=request.user, changes={"order": ids}, request=request)
    return Response(status=status.HTTP_204_NO_CONTENT)


class FilterGroupReorderView(APIView):
    permission_classes = [FILTERS_PERMISSION]

    def post(self, request):
        return _reorder(request, FilterGroup.objects.all(), "filter.group.reorder")


class FilterOptionCreateView(APIView):
    """POST /admin/filters/<groupe>/options {name, nameAr} · POST …/options/reorder {ids}."""

    permission_classes = [FILTERS_PERMISSION]

    def post(self, request, pk):
        group = generics.get_object_or_404(FilterGroup, pk=pk)
        s = FilterOptionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        name = s.validated_data["name"]
        base = unique_slug(name, FilterOption, max_length=80)  # unique globalement : plus simple et sûr
        option = s.save(group=group, slug=base, position=_next_position(group.options))
        log_action(
            "filter.option.create",
            actor=request.user,
            target=option,
            changes={"group": group.name, "name": name},
            request=request,
        )
        return Response(FilterOptionSerializer(option).data, status=status.HTTP_201_CREATED)


class FilterOptionReorderView(APIView):
    permission_classes = [FILTERS_PERMISSION]

    def post(self, request, pk):
        group = generics.get_object_or_404(FilterGroup, pk=pk)
        return _reorder(request, group.options.all(), "filter.option.reorder")


class FilterOptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """PATCH {name, nameAr, isActive} · DELETE : retire la valeur de tous les produits (produits intacts)."""

    serializer_class = FilterOptionSerializer
    permission_classes = [FILTERS_PERMISSION]
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self):
        return FilterOption.objects.annotate(productCount=Count("products"))

    def perform_update(self, serializer):
        option = serializer.save()
        log_action(
            "filter.option.update",
            actor=self.request.user,
            target=option,
            changes=serializer.validated_data,
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_action(
            "filter.option.delete", actor=self.request.user, target=instance,
            changes={"name": instance.name, "products": instance.products.count()}, request=self.request,
        )  # fmt: skip
        instance.delete()


class ProductFiltersSerializer(serializers.Serializer):
    optionIds = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=True, max_length=500)


class ProductFiltersView(APIView):
    """GET /admin/products/<id>/filters → {optionIds} · PUT {optionIds} : remplace les valeurs cochées du produit."""

    permission_classes = [CATALOG_PERMISSION]

    def get(self, request, pk):
        product = generics.get_object_or_404(Product, pk=pk)
        return Response({"optionIds": sorted(product.filter_options.values_list("pk", flat=True))})

    def put(self, request, pk):
        product = generics.get_object_or_404(Product, pk=pk)
        s = ProductFiltersSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ids = sorted(set(s.validated_data["optionIds"]))
        found = set(FilterOption.objects.filter(pk__in=ids).values_list("pk", flat=True))
        if found != set(ids):
            raise serializers.ValidationError({"optionIds": ["Valeur de filtre inconnue."]})
        before = sorted(product.filter_options.values_list("pk", flat=True))
        product.filter_options.set(ids)
        log_action(
            "product.filters", actor=request.user, target=product, changes={"optionIds": [before, ids]}, request=request
        )
        return Response({"optionIds": ids})
