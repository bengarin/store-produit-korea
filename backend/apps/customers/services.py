from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Min, Q, Sum

from .models import Address, Customer


def get_or_create_customer(phone: str, full_name: str) -> Customer:
    """Client identifié par téléphone E.164. Sûr en cas de deux premières commandes simultanées."""
    customer = Customer.objects.select_for_update().filter(phone=phone).first()
    if customer is None:
        try:
            with transaction.atomic():
                customer = Customer.objects.create(phone=phone, full_name=full_name)
        except IntegrityError:
            customer = Customer.objects.select_for_update().get(phone=phone)
    if customer.full_name != full_name and not customer.anonymized_at:
        customer.full_name = full_name
        customer.save(update_fields=["full_name", "updated_at"])
    return customer


def save_address(customer: Customer, *, full_name, phone, city, city_label, address_line) -> Address:
    existing = customer.addresses.filter(city_label=city_label, address_line=address_line).first()
    if existing:
        existing.full_name, existing.phone, existing.city = full_name, phone, city
        existing.save()
        address = existing
    else:
        address = Address.objects.create(
            customer=customer,
            full_name=full_name,
            phone=phone,
            city=city,
            city_label=city_label,
            address_line=address_line,
        )
    customer.addresses.exclude(pk=address.pk).update(is_default=False)
    if not address.is_default:
        address.is_default = True
        address.save(update_fields=["is_default"])
    return address


def refresh_stats(customer: Customer):
    """
    Recalcule depuis les commandes (jamais d'incrément « à la main », donc toujours exact) :
    - orders_count : commandes non annulées
    - total_spent  : total des commandes LIVRÉES (argent réellement encaissé en paiement à la livraison)
    """
    stats = customer.orders.aggregate(
        count=Count("id", filter=~Q(status="cancelled")),
        spent=Sum("total", filter=Q(status="delivered")),
        first=Min("placed_at"),
        last=Max("placed_at"),
    )
    Customer.objects.filter(pk=customer.pk).update(
        orders_count=stats["count"] or 0,
        total_spent=stats["spent"] or 0,
        first_order_at=stats["first"],
        last_order_at=stats["last"],
    )
