from django.urls import path

from . import public

urlpatterns = [
    path("config", public.StoreConfigView.as_view(), name="store-config"),
    path("promo-codes/validate", public.PromoValidateView.as_view(), name="store-promo-validate"),
    path("orders", public.OrderCreateView.as_view(), name="store-orders"),
]
