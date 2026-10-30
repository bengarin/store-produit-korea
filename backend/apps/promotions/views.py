from rest_framework import generics, serializers

from apps.audit.services import log_action
from apps.catalog.permissions import SETTINGS_PERMISSION
from apps.core.http import Conflict

from .models import Coupon


class CouponSerializer(serializers.ModelSerializer):
    minSubtotal = serializers.DecimalField(
        source="min_subtotal", max_digits=10, decimal_places=2, allow_null=True, required=False, min_value=0
    )
    startsAt = serializers.DateTimeField(source="starts_at", allow_null=True, required=False)
    endsAt = serializers.DateTimeField(source="ends_at", allow_null=True, required=False)
    usageLimit = serializers.IntegerField(source="usage_limit", allow_null=True, required=False, min_value=1)
    usageLimitPerCustomer = serializers.IntegerField(
        source="usage_limit_per_customer", allow_null=True, required=False, min_value=1
    )
    isActive = serializers.BooleanField(source="is_active", required=False)
    timesUsed = serializers.SerializerMethodField()
    code = serializers.RegexField(r"^[A-Za-z0-9_-]{3,40}$", max_length=40)

    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "type",
            "value",
            "minSubtotal",
            "startsAt",
            "endsAt",
            "usageLimit",
            "usageLimitPerCustomer",
            "isActive",
            "note",
            "timesUsed",
        ]

    def get_timesUsed(self, coupon):
        return coupon.redemptions.filter(released_at__isnull=True).count()

    def validate_code(self, value):
        value = value.upper()
        if Coupon.objects.filter(code=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Ce code existe déjà.")
        return value

    def validate(self, attrs):
        ctype = attrs.get("type", getattr(self.instance, "type", None))
        value = attrs.get("value", getattr(self.instance, "value", 0))
        if ctype == Coupon.Type.PERCENTAGE and not (0 < value <= 100):
            raise serializers.ValidationError({"value": ["Pourcentage entre 1 et 100."]})
        if ctype == Coupon.Type.FIXED_AMOUNT and value <= 0:
            raise serializers.ValidationError({"value": ["Montant supérieur à 0."]})
        starts = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts and ends and ends <= starts:
            raise serializers.ValidationError({"endsAt": ["La fin doit être après le début."]})
        return attrs


class CouponListCreateView(generics.ListCreateAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [SETTINGS_PERMISSION]

    def perform_create(self, serializer):
        coupon = serializer.save()
        log_action(
            "coupon.create",
            actor=self.request.user,
            target=coupon,
            request=self.request,
            changes={"code": coupon.code, "type": coupon.type, "value": str(coupon.value)},
        )


class CouponDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [SETTINGS_PERMISSION]
    http_method_names = ["get", "patch", "delete"]

    def perform_update(self, serializer):
        coupon = serializer.save()
        log_action(
            "coupon.update",
            actor=self.request.user,
            target=coupon,
            request=self.request,
            changes={k: str(v) for k, v in serializer.validated_data.items()},
        )

    def perform_destroy(self, coupon):
        if coupon.redemptions.exists():
            raise Conflict("Ce code a déjà été utilisé : désactivez-le au lieu de le supprimer.", "coupon_in_use")
        log_action(
            "coupon.delete", actor=self.request.user, target=coupon, request=self.request, changes={"code": coupon.code}
        )
        coupon.delete()
