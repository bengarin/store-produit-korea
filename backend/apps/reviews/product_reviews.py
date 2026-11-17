"""
Avis PRODUITS (fiche produit) — distincts des avis sur la boutique (/avis) et des témoignages du thème.

Boutique : GET  /api/v1/store/products/<slug>/reviews  → avis APPROUVÉS seulement + moyenne et nombre
           POST /api/v1/store/products/<slug>/reviews  → dépôt (statut « En attente », publié après validation)
Admin    : GET/POST /api/v1/admin/product-reviews       (filtres ?status= ?product= ?search=, compteurs)
           GET/PATCH/DELETE /api/v1/admin/product-reviews/<id>

« Achat vérifié » : calculé par le serveur, jamais saisi — avis relié à une commande LIVRÉE contenant le produit.
"""

from django.db.models import Avg, Count, Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem

from .models import ProductReview
from .views import REVIEWS_PERMISSION, _clean_text

MIN_TEXT = 10
MAX_TEXT = 1000


def with_verified(qs):
    """Ajoute `is_verified` (commande liée livrée ET contenant ce produit) en une seule requête."""
    bought = OrderItem.objects.filter(order_id=OuterRef("order_id"), variant__product_id=OuterRef("product_id"))
    return qs.annotate(is_verified=Exists(bought) & Q(order__status=Order.Status.DELIVERED))


def _validate_text(value: str) -> str:
    value = _clean_text(value)
    lowered = value.lower()
    if "http://" in lowered or "https://" in lowered or "www." in lowered:
        raise serializers.ValidationError("Les liens ne sont pas acceptés dans un avis.")
    if len(value) < MIN_TEXT:
        raise serializers.ValidationError(f"Votre avis doit faire au moins {MIN_TEXT} caractères.")
    return value


def _validate_name(value: str) -> str:
    value = " ".join(_clean_text(value).split())
    if len(value) < 2:
        raise serializers.ValidationError("Indiquez au moins 2 caractères.")
    return value


def public_payload(r: ProductReview) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "rating": r.rating,
        "text": r.text,
        "language": r.language,
        "date": (r.approved_at or r.created_at).isoformat(),
        "verifiedPurchase": bool(getattr(r, "is_verified", False)),
    }


def product_reviews_summary(product) -> dict:
    """Avis approuvés d'un produit + moyenne et nombre (API, fiche produit HTML, données structurées)."""
    approved = ProductReview.objects.filter(product=product, status=ProductReview.Status.APPROVED)
    stats = approved.aggregate(count=Count("id"), average=Avg("rating"))
    items = with_verified(approved.select_related("order")).order_by("-approved_at", "-id")[:100]
    return {
        "count": stats["count"],
        "average": round(float(stats["average"]), 1) if stats["average"] is not None else None,
        "items": [public_payload(r) for r in items],
    }


# --- Boutique ------------------------------------------------------------------
class ProductReviewSubmitSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    text = serializers.CharField(max_length=MAX_TEXT)
    language = serializers.ChoiceField(choices=["fr", "ar"], default="fr")
    consent = serializers.BooleanField()
    consentText = serializers.CharField(max_length=240)
    website = serializers.CharField(required=False, allow_blank=True, default="")  # champ piège anti-robots

    validate_name = staticmethod(_validate_name)
    validate_text = staticmethod(_validate_text)

    def validate_consent(self, value):
        if value is not True:
            raise serializers.ValidationError("Votre accord est nécessaire pour publier l'avis.")
        return value

    def validate_consentText(self, value):
        return " ".join(_clean_text(value).split())


class PublicProductReviewsView(APIView):
    """Avis approuvés d'un produit en ligne (GET) et dépôt d'un avis en attente de validation (POST)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "product_reviews"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug, status=Product.Status.ACTIVE)
        return Response(product_reviews_summary(product))

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug, status=Product.Status.ACTIVE)
        s = ProductReviewSubmitSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        # Robot (champ piège) ou doublon exact déjà reçu : même réponse, rien n'est enregistré.
        duplicate = ProductReview.objects.filter(product=product, name=data["name"], text=data["text"]).exists()
        if not data["website"] and not duplicate:
            ProductReview.objects.create(
                product=product,
                name=data["name"],
                rating=data["rating"],
                text=data["text"],
                language=data["language"],
                consent_text=data["consentText"],
            )
        return Response({"ok": True, "status": "pending"}, status=status.HTTP_201_CREATED)


# --- Administration ------------------------------------------------------------
class AdminProductReviewSerializer(serializers.ModelSerializer):
    productId = serializers.PrimaryKeyRelatedField(source="product", queryset=Product.objects.all())
    productName = serializers.CharField(source="product.public_name", read_only=True)
    productSlug = serializers.CharField(source="product.slug", read_only=True)
    orderNumber = serializers.CharField(required=False, allow_blank=True, write_only=True)
    order = serializers.SerializerMethodField()
    sourceNote = serializers.CharField(source="source_note", max_length=200, required=False, allow_blank=True)
    verifiedPurchase = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)
    moderatedAt = serializers.DateTimeField(source="moderated_at", read_only=True)
    approvedAt = serializers.DateTimeField(source="approved_at", read_only=True)
    consentText = serializers.CharField(source="consent_text", read_only=True)
    attestation = serializers.BooleanField(required=False, write_only=True, default=False)

    class Meta:
        model = ProductReview
        fields = [
            "id", "productId", "productName", "productSlug", "name", "rating", "text", "language", "status",
            "source", "sourceNote", "orderNumber", "order", "verifiedPurchase", "consentText", "attestation",
            "createdAt", "updatedAt", "moderatedAt", "approvedAt",
        ]  # fmt: skip
        read_only_fields = ["source"]

    validate_name = staticmethod(_validate_name)
    validate_text = staticmethod(_validate_text)

    def validate_sourceNote(self, value):
        return " ".join(_clean_text(value).split())

    def get_order(self, obj):
        return obj.order.number if obj.order_id else None

    def get_verifiedPurchase(self, obj):
        return bool(getattr(obj, "is_verified", obj.verified_purchase))

    def validate(self, attrs):
        number = attrs.pop("orderNumber", None)
        product = attrs.get("product", self.instance.product if self.instance else None)
        if number is not None:
            number = number.strip()
            if not number:
                attrs["order"] = None
            else:
                order = Order.objects.filter(number=number).first()
                if order is None:
                    raise serializers.ValidationError({"orderNumber": ["Commande introuvable."]})
                if not order.items.filter(variant__product=product).exists():
                    raise serializers.ValidationError({"orderNumber": ["Cette commande ne contient pas ce produit."]})
                attrs["order"] = order
        if self.instance is None:  # saisie manuelle par l'équipe : avis réel uniquement, provenance obligatoire
            if not attrs.pop("attestation", False):
                raise serializers.ValidationError(
                    {"attestation": ["Confirmez que cet avis a bien été écrit par un vrai client."]}
                )
            if not attrs.get("source_note"):
                raise serializers.ValidationError(
                    {"sourceNote": ["Indiquez d'où vient l'avis (ex. message WhatsApp du 12/11)."]}
                )
        else:
            attrs.pop("attestation", None)
        return attrs


def _moderation_fields(new_status, old_status):
    now = timezone.now()
    extra = {}
    if new_status and new_status != old_status:
        extra["moderated_at"] = now
        extra["approved_at"] = now if new_status == ProductReview.Status.APPROVED else None
    return extra


class AdminProductReviewListView(generics.ListCreateAPIView):
    serializer_class = AdminProductReviewSerializer
    permission_classes = [REVIEWS_PERMISSION]

    def get_queryset(self):
        qs = with_verified(ProductReview.objects.select_related("product", "order"))
        params = self.request.query_params
        if params.get("status") in ProductReview.Status.values:
            qs = qs.filter(status=params["status"])
        if params.get("product", "").isdigit():
            qs = qs.filter(product_id=int(params["product"]))
        term = params.get("search", "").strip()
        if term:
            qs = qs.filter(Q(name__icontains=term) | Q(text__icontains=term))
        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        base = ProductReview.objects.all()
        if request.query_params.get("product", "").isdigit():
            base = base.filter(product_id=int(request.query_params["product"]))
        response.data["counts"] = base.aggregate(
            pending=Count("id", filter=Q(status=ProductReview.Status.PENDING)),
            approved=Count("id", filter=Q(status=ProductReview.Status.APPROVED)),
            rejected=Count("id", filter=Q(status=ProductReview.Status.REJECTED)),
        )
        return response

    def perform_create(self, serializer):
        status_value = serializer.validated_data.get("status", ProductReview.Status.PENDING)
        review = serializer.save(
            source=ProductReview.Source.ADMIN,
            created_by=self.request.user,
            consent_text="",
            **_moderation_fields(status_value, ProductReview.Status.PENDING),
        )
        log_action(
            "product_review.create", actor=self.request.user, target=review,
            changes={"product": review.product_id, "status": review.status, "source": review.source_note},
            request=self.request,
        )  # fmt: skip


class AdminProductReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AdminProductReviewSerializer
    permission_classes = [REVIEWS_PERMISSION]
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self):
        return with_verified(ProductReview.objects.select_related("product", "order"))

    def perform_update(self, serializer):
        inst = serializer.instance
        before = {k: getattr(inst, k) for k in ("name", "rating", "text", "status", "order_id")}
        extra = _moderation_fields(serializer.validated_data.get("status"), inst.status)
        review = serializer.save(**extra)
        changes = {k: [v, getattr(review, k)] for k, v in before.items() if getattr(review, k) != v}
        action = (
            {
                ProductReview.Status.APPROVED: "product_review.approve",
                ProductReview.Status.REJECTED: "product_review.reject",
            }.get(review.status)
            if "status" in changes
            else "product_review.update"
        )
        log_action(action, actor=self.request.user, target=review, changes=changes, request=self.request)

    def perform_destroy(self, instance):
        log_action(
            "product_review.delete", actor=self.request.user, target=instance,
            changes={"product": instance.product_id, "name": instance.name, "rating": instance.rating},
            request=self.request,
        )  # fmt: skip
        instance.delete()
