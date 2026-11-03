from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.catalog.permissions import SETTINGS_PERMISSION

from .models import StoreSettings


class SettingsSerializer(serializers.ModelSerializer):
    brandName = serializers.CharField(source="brand_name", max_length=100)
    whatsappNumber = serializers.RegexField(
        r"^\d{8,15}$", source="whatsapp_number", allow_blank=True, required=False, max_length=20
    )
    contactEmail = serializers.EmailField(source="contact_email", allow_blank=True, required=False)
    contactPhone = serializers.CharField(source="contact_phone", allow_blank=True, required=False, max_length=20)
    legalName = serializers.CharField(source="legal_name", allow_blank=True, required=False, max_length=150)
    legalAddress = serializers.CharField(source="legal_address", allow_blank=True, required=False)
    ifNumber = serializers.CharField(source="if_number", allow_blank=True, required=False, max_length=30)
    invoiceFooter = serializers.CharField(source="invoice_footer", allow_blank=True, required=False, max_length=255)
    ice = serializers.RegexField(
        r"^(\d{15})?$",
        allow_blank=True,
        required=False,
        max_length=15,
        error_messages={"invalid": "L'ICE comporte 15 chiffres."},
    )
    patente = serializers.CharField(allow_blank=True, required=False, max_length=30)
    invoicePrefix = serializers.RegexField(
        r"^[A-Z]{1,6}$",
        source="invoice_prefix",
        required=False,
        error_messages={"invalid": "1 à 6 lettres majuscules (ex. FAC)."},
    )
    vatRate = serializers.DecimalField(
        source="vat_rate", max_digits=5, decimal_places=2, min_value=0, max_value=100, allow_null=True, required=False
    )
    deliveryMode = serializers.ChoiceField(
        source="delivery_mode", choices=StoreSettings.DeliveryMode.choices, required=False
    )
    deliveryFee = serializers.DecimalField(
        source="delivery_fee",
        max_digits=10,
        decimal_places=2,
        min_value=0,
        max_value=10000,
        allow_null=True,
        required=False,
    )
    maxQtyPerLine = serializers.IntegerField(source="max_qty_per_line", min_value=1, max_value=100, required=False)
    maxOrdersPerPhonePerHour = serializers.IntegerField(
        source="max_orders_per_phone_per_hour", min_value=1, max_value=100, required=False
    )

    class Meta:
        model = StoreSettings
        fields = [
            "brandName",
            "whatsappNumber",
            "contactEmail",
            "contactPhone",
            "legalName",
            "legalAddress",
            "ice",
            "rc",
            "ifNumber",
            "patente",
            "invoiceFooter",
            "invoicePrefix",
            "vatRate",
            "deliveryMode",
            "deliveryFee",
            "maxQtyPerLine",
            "maxOrdersPerPhonePerHour",
        ]

    def validate(self, attrs):
        # Valeurs finales (modification partielle) : le mode payant exige un montant > 0, saisi par l'admin.
        mode = attrs.get("delivery_mode", self.instance.delivery_mode if self.instance else None)
        fee = attrs.get("delivery_fee", self.instance.delivery_fee if self.instance else None)
        if mode == StoreSettings.DeliveryMode.PAID and (fee is None or fee <= 0):
            raise serializers.ValidationError(
                {"deliveryFee": ["Indiquez le montant des frais de livraison (supérieur à 0 DH)."]}
            )
        return attrs


class SettingsView(APIView):
    permission_classes = [SETTINGS_PERMISSION]

    def get(self, request):
        return Response(SettingsSerializer(StoreSettings.load()).data)

    def patch(self, request):
        serializer = SettingsSerializer(StoreSettings.load(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(
            "settings.update",
            actor=request.user,
            request=request,
            changes={k: str(v) for k, v in serializer.validated_data.items()},
        )
        return Response(serializer.data)
