from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.blog.permissions import BLOG_PERMISSION

from .models import StoreReview

# Modération : mêmes rôles que les contenus (Propriétaire, Admin, Éditeur) ; suppression : Propriétaire, Admin.
REVIEWS_PERMISSION = BLOG_PERMISSION


def _clean_text(value: str) -> str:
    if "<" in value or ">" in value:
        raise serializers.ValidationError("Les caractères < et > ne sont pas acceptés.")
    return value.strip()


def public_payload(r: StoreReview) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "rating": r.rating,
        "text": r.text,
        "language": r.language,
        "date": (r.approved_at or r.created_at).isoformat(),
    }


# --- Boutique ------------------------------------------------------------------
class ReviewSubmitSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    text = serializers.CharField(max_length=1000, min_length=10)
    language = serializers.ChoiceField(choices=["fr", "ar"], default="fr")
    consent = serializers.BooleanField()
    consentText = serializers.CharField(max_length=240)
    website = serializers.CharField(required=False, allow_blank=True, default="")  # champ piège anti-robots

    def validate_name(self, value):
        value = " ".join(_clean_text(value).split())
        if len(value) < 2:
            raise serializers.ValidationError("Indiquez au moins 2 caractères.")
        return value

    def validate_text(self, value):
        value = _clean_text(value)
        lowered = value.lower()
        if "http://" in lowered or "https://" in lowered or "www." in lowered:
            raise serializers.ValidationError("Les liens ne sont pas acceptés dans un avis.")
        return value

    def validate_consent(self, value):
        if value is not True:
            raise serializers.ValidationError("Votre accord est nécessaire pour publier l'avis.")
        return value

    def validate_consentText(self, value):
        return " ".join(_clean_text(value).split())


class PublicReviewsView(APIView):
    """
    GET  /api/v1/store/reviews — avis approuvés + moyenne et nombre.
    POST /api/v1/store/reviews — dépôt d'un avis (statut « En attente », publié après validation).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "reviews"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get(self, request):
        approved = StoreReview.objects.filter(status=StoreReview.Status.APPROVED)
        stats = approved.aggregate(count=Count("id"), average=Avg("rating"))
        return Response(
            {
                "count": stats["count"],
                "average": round(float(stats["average"]), 1) if stats["average"] is not None else None,
                "items": [public_payload(r) for r in approved.order_by("-approved_at", "-id")[:100]],
            }
        )

    def post(self, request):
        s = ReviewSubmitSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        if not data["website"]:  # robot : même réponse, rien n'est enregistré
            StoreReview.objects.create(
                name=data["name"],
                rating=data["rating"],
                text=data["text"],
                language=data["language"],
                consent_text=data["consentText"],
            )
        return Response({"ok": True, "status": "pending"}, status=201)


# --- Administration ------------------------------------------------------------
class AdminReviewSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    approvedAt = serializers.DateTimeField(source="approved_at", read_only=True)
    consentText = serializers.CharField(source="consent_text", read_only=True)

    class Meta:
        model = StoreReview
        fields = ["id", "name", "rating", "text", "language", "status", "consentText", "createdAt", "approvedAt"]
        read_only_fields = ["language"]

    def validate_name(self, value):
        value = " ".join(_clean_text(value).split())
        if len(value) < 2:
            raise serializers.ValidationError("Indiquez au moins 2 caractères.")
        return value

    def validate_text(self, value):
        value = _clean_text(value)
        if not value:
            raise serializers.ValidationError("Le texte est obligatoire.")
        return value


class AdminReviewListView(generics.ListAPIView):
    """GET /api/v1/admin/reviews (?status=pending|approved, ?search=) + compteurs par statut."""

    serializer_class = AdminReviewSerializer
    permission_classes = [REVIEWS_PERMISSION]

    def get_queryset(self):
        qs = StoreReview.objects.all()
        params = self.request.query_params
        if params.get("status") in StoreReview.Status.values:
            qs = qs.filter(status=params["status"])
        term = params.get("search", "").strip()
        if term:
            qs = qs.filter(Q(name__icontains=term) | Q(text__icontains=term))
        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        counts = StoreReview.objects.aggregate(
            pending=Count("id", filter=Q(status=StoreReview.Status.PENDING)),
            approved=Count("id", filter=Q(status=StoreReview.Status.APPROVED)),
        )
        response.data["counts"] = counts
        return response


class AdminReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """PATCH : corriger nom / note / texte, approuver (status=approved) ou dépublier (status=pending) · DELETE."""

    queryset = StoreReview.objects.all()
    serializer_class = AdminReviewSerializer
    permission_classes = [REVIEWS_PERMISSION]
    http_method_names = ["get", "patch", "delete"]

    def perform_update(self, serializer):
        before = {k: getattr(serializer.instance, k) for k in ("name", "rating", "text", "status")}
        extra = {}
        new_status = serializer.validated_data.get("status")
        if new_status == StoreReview.Status.APPROVED and before["status"] != StoreReview.Status.APPROVED:
            extra["approved_at"] = timezone.now()
        elif new_status == StoreReview.Status.PENDING:
            extra["approved_at"] = None
        review = serializer.save(**extra)
        changes = {k: [v, getattr(review, k)] for k, v in before.items() if getattr(review, k) != v}
        action = "review.approve" if extra.get("approved_at") else "review.update"
        log_action(action, actor=self.request.user, target=review, changes=changes, request=self.request)

    def perform_destroy(self, instance):
        log_action(
            "review.delete", actor=self.request.user, target=instance,
            changes={"name": instance.name, "rating": instance.rating}, request=self.request,
        )  # fmt: skip
        instance.delete()
