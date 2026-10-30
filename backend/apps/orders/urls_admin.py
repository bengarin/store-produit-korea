from django.urls import path

from apps.analytics import views as analytics_views
from apps.customers import views as customer_views
from apps.inventory import views as inventory_views
from apps.promotions import views as promo_views
from apps.shipping import views as shipping_views
from apps.store_settings import views as settings_views

from . import admin_api

urlpatterns = [
    path("orders", admin_api.OrderListView.as_view(), name="admin-orders"),
    path("orders/export.xlsx", admin_api.OrderExportView.as_view(), name="admin-orders-export"),
    path("orders/<int:pk>", admin_api.OrderDetailView.as_view(), name="admin-order"),
    path("orders/<int:pk>/status", admin_api.OrderStatusView.as_view(), name="admin-order-status"),
    path("orders/<int:pk>/invoice", admin_api.OrderInvoiceView.as_view(), name="admin-order-invoice"),
    path("customers", customer_views.CustomerListView.as_view(), name="admin-customers"),
    path("customers/<int:pk>", customer_views.CustomerDetailView.as_view(), name="admin-customer"),
    path("inventory", inventory_views.InventoryListView.as_view(), name="admin-inventory"),
    path("inventory/adjust", inventory_views.AdjustView.as_view(), name="admin-inventory-adjust"),
    path("inventory/movements", inventory_views.MovementListView.as_view(), name="admin-inventory-movements"),
    path("coupons", promo_views.CouponListCreateView.as_view(), name="admin-coupons"),
    path("coupons/<int:pk>", promo_views.CouponDetailView.as_view(), name="admin-coupon"),
    path("shipping/zones", shipping_views.ZoneListCreateView.as_view(), name="admin-zones"),
    path("shipping/zones/<int:pk>", shipping_views.ZoneDetailView.as_view(), name="admin-zone"),
    path("shipping/cities", shipping_views.CityListCreateView.as_view(), name="admin-cities"),
    path("shipping/cities/<int:pk>", shipping_views.CityDetailView.as_view(), name="admin-city"),
    path("settings", settings_views.SettingsView.as_view(), name="admin-settings"),
    path("analytics/report", analytics_views.ReportView.as_view(), name="admin-analytics-report"),
    path("analytics/export", analytics_views.ReportExportView.as_view(), name="admin-analytics-export"),
]
