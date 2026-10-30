from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.catalog.permissions import ORDERS_PERMISSION
from apps.orders.serializers import OrderListSerializer

from .models import Address, Customer


class CustomerSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(source="full_name", read_only=True)
    ordersCount = serializers.IntegerField(source="orders_count", read_only=True)
    totalSpent = serializers.DecimalField(source="total_spent", max_digits=12, decimal_places=2, read_only=True)
    firstOrderAt = serializers.DateTimeField(source="first_order_at", read_only=True)
    lastOrderAt = serializers.DateTimeField(source="last_order_at", read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "fullName",
            "phone",
            "email",
            "notes",
            "ordersCount",
            "totalSpent",
            "firstOrderAt",
            "lastOrderAt",
        ]
        read_only_fields = ["phone"]


class AddressSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(source="full_name")
    city = serializers.CharField(source="city_label")
    address = serializers.CharField(source="address_line")
    isDefault = serializers.BooleanField(source="is_default")

    class Meta:
        model = Address
        fields = ["id", "fullName", "phone", "city", "address", "isDefault"]


class CustomerListView(generics.ListAPIView):
    """?search=nom ou téléphone · ?ordering=-last_order_at|-total_spent|-orders_count|full_name"""

    serializer_class = CustomerSerializer
    permission_classes = [ORDERS_PERMISSION]
    ORDERINGS = {"-last_order_at", "-total_spent", "-orders_count", "full_name", "-created_at"}

    def get_queryset(self):
        qs = Customer.objects.all()
        term = self.request.query_params.get("search", "").strip()
        if term:
            digits = "".join(c for c in term if c.isdigit())
            cond = Q(full_name__icontains=term)
            if len(digits) >= 6:
                cond |= Q(phone__contains=digits[-9:])
            qs = qs.filter(cond)
        ordering = self.request.query_params.get("ordering")
        return qs.order_by(ordering, "-id") if ordering in self.ORDERINGS else qs


class CustomerDetailView(APIView):
    """Fiche client + historique d'achats complet + adresses."""

    permission_classes = [ORDERS_PERMISSION]

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        data = CustomerSerializer(customer).data
        data["addresses"] = AddressSerializer(customer.addresses.all(), many=True).data
        data["orders"] = OrderListSerializer(customer.orders.order_by("-placed_at"), many=True).data
        return Response(data)

    def patch(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        serializer = CustomerSerializer(customer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(
            "customer.update",
            actor=request.user,
            target=customer,
            request=request,
            changes={k: "modifié" for k in serializer.validated_data},
        )
        return self.get(request, pk)
