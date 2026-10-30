from django.db import transaction
from rest_framework import generics, serializers

from apps.audit.services import log_action
from apps.catalog.permissions import SETTINGS_PERMISSION

from .models import City, ShippingZone


class ZoneSerializer(serializers.ModelSerializer):
    freeOverSubtotal = serializers.DecimalField(
        source="free_over_subtotal", max_digits=10, decimal_places=2, allow_null=True, required=False, min_value=0
    )
    deliveryDaysMin = serializers.IntegerField(source="delivery_days_min", allow_null=True, required=False)
    deliveryDaysMax = serializers.IntegerField(source="delivery_days_max", allow_null=True, required=False)
    isDefault = serializers.BooleanField(source="is_default", required=False)
    isActive = serializers.BooleanField(source="is_active", required=False)
    fee = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    cityCount = serializers.IntegerField(source="cities.count", read_only=True)

    class Meta:
        model = ShippingZone
        fields = [
            "id",
            "name",
            "fee",
            "freeOverSubtotal",
            "deliveryDaysMin",
            "deliveryDaysMax",
            "isDefault",
            "isActive",
            "cityCount",
        ]


class CitySerializer(serializers.ModelSerializer):
    zoneId = serializers.PrimaryKeyRelatedField(source="zone", queryset=ShippingZone.objects.all())
    isActive = serializers.BooleanField(source="is_active", required=False)

    class Meta:
        model = City
        fields = ["id", "name", "zoneId", "position", "isActive"]


class _Audited:
    action = ""

    def perform_create(self, serializer):
        obj = self._save(serializer)
        log_action(
            f"{self.action}.create",
            actor=self.request.user,
            target=obj,
            request=self.request,
            changes={k: str(v) for k, v in serializer.validated_data.items()},
        )

    def perform_update(self, serializer):
        obj = self._save(serializer)
        log_action(
            f"{self.action}.update",
            actor=self.request.user,
            target=obj,
            request=self.request,
            changes={k: str(v) for k, v in serializer.validated_data.items()},
        )

    @transaction.atomic
    def _save(self, serializer):
        obj = serializer.save()
        if isinstance(obj, ShippingZone) and obj.is_default:  # une seule zone par défaut
            ShippingZone.objects.exclude(pk=obj.pk).update(is_default=False)
        return obj


class ZoneListCreateView(_Audited, generics.ListCreateAPIView):
    queryset = ShippingZone.objects.all()
    serializer_class = ZoneSerializer
    permission_classes = [SETTINGS_PERMISSION]
    pagination_class = None
    action = "shipping_zone"


class ZoneDetailView(_Audited, generics.RetrieveUpdateAPIView):
    queryset = ShippingZone.objects.all()
    serializer_class = ZoneSerializer
    permission_classes = [SETTINGS_PERMISSION]
    http_method_names = ["get", "patch"]
    action = "shipping_zone"


class CityListCreateView(_Audited, generics.ListCreateAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = [SETTINGS_PERMISSION]
    pagination_class = None
    action = "city"


class CityDetailView(_Audited, generics.RetrieveUpdateAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = [SETTINGS_PERMISSION]
    http_method_names = ["get", "patch"]
    action = "city"
