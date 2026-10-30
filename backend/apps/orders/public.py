"""API publique de commande (sans session) : /api/v1/store/config, /promo-codes/validate, /orders."""

import re

from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.core.money import number
from apps.core.phone import normalize_moroccan_phone
from apps.promotions import services as promotions
from apps.shipping.models import City, ShippingZone
from apps.store_settings.models import StoreSettings

from . import services

IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9-]{16,64}$")
HONEYPOT_FIELD = "website"  # champ invisible du formulaire : un humain ne le remplit jamais


class ItemSerializer(serializers.Serializer):
    productId = serializers.SlugField(max_length=120)
    variantId = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    qty = serializers.IntegerField(min_value=1, max_value=100)


class CustomerSerializer(serializers.Serializer):
    fullName = serializers.CharField(min_length=3, max_length=120)
    phone = serializers.CharField(max_length=30)
    city = serializers.CharField(min_length=2, max_length=80)
    address = serializers.CharField(min_length=8, max_length=255)

    def validate_phone(self, value):
        phone = normalize_moroccan_phone(value)
        if phone is None:
            raise serializers.ValidationError("Numéro marocain invalide (ex. 06 12 34 56 78 ou +212 6 12 34 56 78).")
        return phone

    def validate_fullName(self, value):
        return " ".join(value.split())

    def validate_address(self, value):
        return " ".join(value.split())


class OrderRequestSerializer(serializers.Serializer):
    customer = CustomerSerializer()
    items = ItemSerializer(many=True, allow_empty=False, max_length=30)
    promoCode = serializers.CharField(max_length=40, required=False, allow_blank=True, allow_null=True)
    paymentMethod = serializers.ChoiceField(choices=["cod"], default="cod")
    deliveryMethod = serializers.ChoiceField(choices=["home"], default="home")
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class PublicView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # pas de session : rien à voler par CSRF


class StoreConfigView(PublicView):
    """Configuration publique (format de src/config/store.js). Jamais les codes promo."""

    def get(self, request):
        settings = StoreSettings.load()
        default_zone = ShippingZone.objects.filter(is_default=True, is_active=True).first()
        reference = default_zone or ShippingZone.objects.filter(is_active=True).order_by("fee").first()
        return Response(
            {
                "brandName": settings.brand_name,
                "whatsappNumber": settings.whatsapp_number,
                "deliveryFee": number(reference.fee) if reference else None,
                "freeDeliveryThreshold": number(reference.free_over_subtotal) if reference else None,
                "cities": list(
                    City.objects.filter(is_active=True, zone__is_active=True).values_list("name", flat=True)
                ),
                "allowOtherCity": default_zone is not None,
                "maxQtyPerLine": settings.max_qty_per_line,
            }
        )


class PromoValidateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=40)
    items = ItemSerializer(many=True, allow_empty=False, max_length=30)


class PromoValidateView(PublicView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "promo"

    def post(self, request):
        data = PromoValidateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        lines = services.resolve_lines(data.validated_data["items"])
        subtotal = sum((line.line_total for line in lines), start=0)
        try:
            result = promotions.evaluate(data.validated_data["code"], subtotal=subtotal)
        except promotions.CouponError as exc:
            return Response({"valid": False, "message": str(exc)})
        return Response({"valid": True, **promotions.public_payload(result)})


class OrderCreateView(PublicView):
    """
    POST /api/v1/store/orders — en-tête Idempotency-Key obligatoire (UUID généré par le navigateur).
    201 : commande créée · 200 : même commande renvoyée (renvoi de la même requête)
    409 insufficient_stock : détail par article dans error.items
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "orders"

    def post(self, request):
        if (request.data.get(HONEYPOT_FIELD) or "").strip():
            log_action("order.spam_blocked", request=request, changes={"reason": "honeypot"})
            raise serializers.ValidationError("Requête refusée.")
        key = request.headers.get("Idempotency-Key", "")
        if not IDEMPOTENCY_KEY.match(key):
            raise serializers.ValidationError({"idempotencyKey": ["En-tête Idempotency-Key manquant ou invalide."]})
        data = OrderRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        payload = dict(data.validated_data)
        payload["customer"] = dict(payload["customer"])
        payload["items"] = [dict(i) for i in payload["items"]]
        order, created = services.create_order(payload, idempotency_key=key, request=request)
        return Response(
            services.order_response(order), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
