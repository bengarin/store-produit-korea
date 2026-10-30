from django.db.models import F, Q
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Variant
from apps.catalog.permissions import INVENTORY_PERMISSION
from apps.core.filters import date_range

from . import services
from .models import StockMovement


def stock_state(v: Variant) -> str:
    if not v.track_inventory:
        return "not_tracked"
    if v.stock_quantity is None:
        return "unknown"
    if v.stock_quantity <= 0:
        return "out_of_stock"
    if v.stock_quantity <= v.low_stock_threshold:
        return "low"
    return "ok"


class InventoryItemSerializer(serializers.ModelSerializer):
    productId = serializers.IntegerField(source="product_id")
    productSlug = serializers.CharField(source="product.slug")
    productName = serializers.CharField(source="product.public_name")
    productStatus = serializers.CharField(source="product.status")
    stockQuantity = serializers.IntegerField(source="stock_quantity", allow_null=True)
    lowStockThreshold = serializers.IntegerField(source="low_stock_threshold")
    trackInventory = serializers.BooleanField(source="track_inventory")
    allowBackorder = serializers.BooleanField(source="allow_backorder")
    state = serializers.SerializerMethodField()
    productImage = serializers.SerializerMethodField()

    class Meta:
        model = Variant
        fields = [
            "id",
            "productId",
            "productSlug",
            "productName",
            "productStatus",
            "productImage",
            "title",
            "sku",
            "stockQuantity",
            "lowStockThreshold",
            "trackInventory",
            "allowBackorder",
            "state",
        ]

    def get_state(self, v):
        return stock_state(v)

    def get_productImage(self, v):
        first = v.product.images.filter(in_gallery=True).select_related("media").order_by("position", "id").first()
        return (first.media.url_640 or first.media.url) if first else None


class InventoryListView(generics.ListAPIView):
    """?state=unknown|low|out_of_stock · ?search=produit ou SKU"""

    serializer_class = InventoryItemSerializer
    permission_classes = [INVENTORY_PERMISSION]

    def get_queryset(self):
        qs = (
            Variant.objects.select_related("product")
            .exclude(product__status="archived")
            .order_by("product__position", "position", "id")
        )
        state = self.request.query_params.get("state")
        tracked = Q(track_inventory=True)
        if state == "unknown":
            qs = qs.filter(tracked, stock_quantity__isnull=True)
        elif state == "out_of_stock":
            qs = qs.filter(tracked, stock_quantity__lte=0)
        elif state == "low":
            qs = qs.filter(tracked, stock_quantity__gt=0, stock_quantity__lte=F("low_stock_threshold"))
        term = self.request.query_params.get("search", "").strip()
        if term:
            qs = qs.filter(
                Q(product__name__icontains=term)
                | Q(product__brand__icontains=term)
                | Q(product__display_name__icontains=term)
                | Q(sku__iexact=term)
            )
        return qs


class AdjustSerializer(serializers.Serializer):
    variantId = serializers.IntegerField(min_value=1)
    mode = serializers.ChoiceField(choices=["set", "delta"])
    quantity = serializers.IntegerField(min_value=-100000, max_value=100000)
    reason = serializers.ChoiceField(choices=sorted(StockMovement.MANUAL_REASONS))
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["reason"] == "manual_adjustment" and not attrs["note"].strip():
            raise serializers.ValidationError({"note": ["Expliquez la raison de cette correction manuelle."]})
        return attrs


class MovementSerializer(serializers.ModelSerializer):
    variantId = serializers.IntegerField(source="variant_id")
    productName = serializers.CharField(source="variant.product.public_name")
    variantTitle = serializers.CharField(source="variant.title")
    quantityBefore = serializers.IntegerField(source="quantity_before", allow_null=True)
    quantityAfter = serializers.IntegerField(source="quantity_after", allow_null=True)
    reasonLabel = serializers.CharField(source="get_reason_display")
    orderNumber = serializers.CharField(source="order.number", default=None)
    user = serializers.CharField(source="user.email", default=None)
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "variantId",
            "productName",
            "variantTitle",
            "delta",
            "quantityBefore",
            "quantityAfter",
            "reason",
            "reasonLabel",
            "note",
            "orderNumber",
            "user",
            "createdAt",
        ]


class AdjustView(APIView):
    """POST {"variantId", "mode": "set"|"delta", "quantity", "reason", "note"}"""

    permission_classes = [INVENTORY_PERMISSION]

    def post(self, request):
        data = AdjustSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        if not Variant.objects.filter(pk=d["variantId"]).exists():
            raise serializers.ValidationError({"variantId": ["Variante introuvable."]})
        movement = services.adjust_stock(
            d["variantId"],
            mode=d["mode"],
            quantity=d["quantity"],
            reason=d["reason"],
            note=d["note"],
            user=request.user,
            request=request,
        )
        movement = StockMovement.objects.select_related("variant__product", "order", "user").get(pk=movement.pk)
        return Response(MovementSerializer(movement).data, status=status.HTTP_201_CREATED)


class MovementListView(generics.ListAPIView):
    """?variant=<id> · ?product=<id> · ?reason= · ?order=<numéro> · ?from=&to="""

    serializer_class = MovementSerializer
    permission_classes = [INVENTORY_PERMISSION]

    def get_queryset(self):
        p = self.request.query_params
        qs = StockMovement.objects.select_related("variant__product", "order", "user")
        if p.get("variant", "").isdigit():
            qs = qs.filter(variant_id=p["variant"])
        if p.get("product", "").isdigit():
            qs = qs.filter(variant__product_id=p["product"])
        if p.get("reason") in StockMovement.Reason.values:
            qs = qs.filter(reason=p["reason"])
        if p.get("order"):
            qs = qs.filter(order__number=p["order"])
        return qs.filter(**date_range(p, "created_at"))
