from django.db import models


class Customer(models.Model):
    """
    Client de la boutique (sans compte), identifié par son téléphone normalisé E.164.
    Jamais supprimé s'il a des commandes (PROTECT côté commande) : on l'anonymise.
    `orders_count` et `total_spent` sont RECALCULÉS depuis les commandes (customers.services.refresh_stats).
    """

    phone = models.CharField("téléphone (E.164)", max_length=16, unique=True)
    full_name = models.CharField("nom complet", max_length=120)
    email = models.EmailField(blank=True)
    notes = models.TextField("notes internes", blank=True)
    orders_count = models.PositiveIntegerField("commandes (hors annulées)", default=0)
    total_spent = models.DecimalField("total encaissé (DH)", max_digits=12, decimal_places=2, default=0)
    first_order_at = models.DateTimeField(null=True, blank=True)
    last_order_at = models.DateTimeField(null=True, blank=True, db_index=True)
    anonymized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "client"
        ordering = ["-last_order_at", "-id"]
        indexes = [models.Index(fields=["full_name"], name="customer_name_idx")]

    def __str__(self):
        return f"{self.full_name} ({self.phone})"


class Address(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=16)
    city = models.ForeignKey("shipping.City", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    city_label = models.CharField("ville", max_length=80)
    address_line = models.CharField("adresse", max_length=255)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "adresse"
        ordering = ["-last_used_at", "-id"]

    def __str__(self):
        return f"{self.address_line}, {self.city_label}"
