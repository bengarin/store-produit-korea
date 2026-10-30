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
            "invoiceFooter",
            "maxQtyPerLine",
            "maxOrdersPerPhonePerHour",
        ]


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
