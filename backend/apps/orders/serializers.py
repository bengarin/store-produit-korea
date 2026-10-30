from rest_framework import serializers

from apps.catalog.permissions import COST_VIEW

from .models import Order, OrderItem, OrderStatusHistory


def _role(context):
    return getattr(getattr(context.get("request"), "user", None), "role", None)


class OrderItemSerializer(serializers.ModelSerializer):
    productSlug = serializers.CharField(source="product_slug")
    productName = serializers.CharField(source="product_name")
    variantId = serializers.IntegerField(source="variant_id")
    variantTitle = serializers.CharField(source="variant_title")
    unitPrice = serializers.DecimalField(source="unit_price", max_digits=10, decimal_places=2)
    unitCost = serializers.DecimalField(source="unit_cost", max_digits=10, decimal_places=2)
    lineTotal = serializers.DecimalField(source="line_total", max_digits=12, decimal_places=2)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "productSlug",
            "productName",
            "variantId",
            "variantTitle",
            "sku",
            "unitPrice",
            "unitCost",
            "quantity",
            "lineTotal",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if _role(self.context) not in COST_VIEW:
            data.pop("unitCost", None)
        return data


class HistorySerializer(serializers.ModelSerializer):
    fromStatus = serializers.CharField(source="from_status")
    toStatus = serializers.CharField(source="to_status")
    changedBy = serializers.CharField(source="changed_by.email", default=None)
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = OrderStatusHistory
        fields = ["fromStatus", "toStatus", "changedBy", "note", "createdAt"]


class OrderListSerializer(serializers.ModelSerializer):
    customerName = serializers.CharField(source="ship_full_name")
    phone = serializers.CharField(source="ship_phone")
    city = serializers.CharField(source="ship_city_label")
    itemCount = serializers.IntegerField(source="item_count")
    paymentStatus = serializers.CharField(source="payment_status")
    placedAt = serializers.DateTimeField(source="placed_at")

    class Meta:
        model = Order
        fields = [
            "id",
            "number",
            "status",
            "paymentStatus",
            "customerName",
            "phone",
            "city",
            "itemCount",
            "total",
            "placedAt",
        ]


class OrderDetailSerializer(OrderListSerializer):
    customerId = serializers.IntegerField(source="customer_id")
    address = serializers.CharField(source="ship_address")
    shippingZone = serializers.CharField(source="shipping_zone_name")
    paymentMethod = serializers.CharField(source="payment_method")
    discount = serializers.DecimalField(source="discount_total", max_digits=12, decimal_places=2)
    shippingFee = serializers.DecimalField(source="shipping_fee", max_digits=10, decimal_places=2)
    couponCode = serializers.CharField(source="coupon_code")
    customerNote = serializers.CharField(source="customer_note")
    internalNote = serializers.CharField(source="internal_note")
    items = OrderItemSerializer(many=True)
    history = HistorySerializer(many=True)
    allowedTransitions = serializers.SerializerMethodField()

    class Meta(OrderListSerializer.Meta):
        fields = [
            *OrderListSerializer.Meta.fields,
            "customerId",
            "address",
            "shippingZone",
            "paymentMethod",
            "subtotal",
            "discount",
            "shippingFee",
            "couponCode",
            "customerNote",
            "internalNote",
            "items",
            "history",
            "allowedTransitions",
        ]

    def get_allowedTransitions(self, order):
        from .services import TRANSITIONS

        return sorted(TRANSITIONS.get(order.status, set()))


class StatusChangeSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    restock = serializers.BooleanField(required=False, default=True)


class OrderUpdateSerializer(serializers.Serializer):
    internalNote = serializers.CharField(allow_blank=True, max_length=5000)
