from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.catalog.permissions import ORDERS_PERMISSION
from apps.core.filters import date_range
from apps.store_settings.models import StoreSettings

from . import services
from .exports import orders_workbook
from .models import Order, OrderStatusHistory
from .serializers import OrderDetailSerializer, OrderListSerializer, OrderUpdateSerializer, StatusChangeSerializer


def filtered_orders(params):
    """?status= · ?payment= · ?from=AAAA-MM-JJ&to= · ?city= · ?search=n°, téléphone ou nom · ?customer=<id>"""
    qs = Order.objects.all()
    if params.get("status") in Order.Status.values:
        qs = qs.filter(status=params["status"])
    if params.get("payment") in Order.PaymentStatus.values:
        qs = qs.filter(payment_status=params["payment"])
    if params.get("city"):
        qs = qs.filter(ship_city_label__iexact=params["city"])
    if params.get("customer", "").isdigit():
        qs = qs.filter(customer_id=params["customer"])
    qs = qs.filter(**date_range(params))
    term = params.get("search", "").strip()
    if term:
        digits = "".join(c for c in term if c.isdigit())
        cond = Q(number__icontains=term) | Q(ship_full_name__icontains=term)
        if len(digits) >= 6:
            cond |= Q(ship_phone__contains=digits[-9:])
        qs = qs.filter(cond)
    return qs


class OrderListView(generics.ListAPIView):
    serializer_class = OrderListSerializer
    permission_classes = [ORDERS_PERMISSION]

    def get_queryset(self):
        return filtered_orders(self.request.query_params)


def order_detail_queryset():
    return Order.objects.prefetch_related(
        "items", Prefetch("history", queryset=OrderStatusHistory.objects.select_related("changed_by"))
    )


class OrderDetailView(APIView):
    permission_classes = [ORDERS_PERMISSION]

    def get(self, request, pk):
        order = get_object_or_404(order_detail_queryset(), pk=pk)
        return Response(OrderDetailSerializer(order, context={"request": request}).data)

    def patch(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        data = OrderUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        order.internal_note = data.validated_data["internalNote"]
        order.save(update_fields=["internal_note", "updated_at"])
        log_action("order.note", actor=request.user, target=order, request=request)
        order = get_object_or_404(order_detail_queryset(), pk=pk)
        return Response(OrderDetailSerializer(order, context={"request": request}).data)


class OrderStatusView(APIView):
    """POST {"status": "cancelled", "note": "…", "restock": true}"""

    permission_classes = [ORDERS_PERMISSION]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        data = StatusChangeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.change_status(
            order,
            data.validated_data["status"],
            user=request.user,
            note=data.validated_data["note"],
            restock=data.validated_data["restock"],
            request=request,
        )
        order = get_object_or_404(order_detail_queryset(), pk=pk)
        return Response(OrderDetailSerializer(order, context={"request": request}).data)


class OrderInvoiceView(APIView):
    """Facture HTML imprimable (ouvrir dans un onglet puis Imprimer / PDF)."""

    permission_classes = [ORDERS_PERMISSION]

    def get(self, request, pk):
        order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
        html = render_to_string(
            "orders/invoice.html",
            {
                "order": order,
                "items": order.items.all(),
                "settings": StoreSettings.load(),
                "placed_at": timezone.localtime(order.placed_at),
            },
        )
        log_action("order.invoice", actor=request.user, target=order, request=request)
        response = HttpResponse(html, content_type="text/html; charset=utf-8")
        response["X-Frame-Options"] = "SAMEORIGIN"
        response["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'"
        )
        return response


class OrderExportView(APIView):
    """Export Excel des commandes filtrées (mêmes filtres que la liste)."""

    permission_classes = [ORDERS_PERMISSION]

    def get(self, request):
        orders = filtered_orders(request.query_params).order_by("placed_at")[:10000]
        content = orders_workbook(orders)
        log_action(
            "order.export",
            actor=request.user,
            request=request,
            changes={"filters": dict(request.query_params.items()), "count": len(orders)},
        )
        response = HttpResponse(
            content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
        response["Content-Disposition"] = f'attachment; filename="commandes-{stamp}.xlsx"'
        return response
