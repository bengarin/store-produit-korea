from django.utils import timezone
from rest_framework import serializers

from apps.catalog.services import unique_slug
from apps.core.html import sanitize_html
from apps.media_library.models import MediaAsset

from .models import Article
from .public import cover_payload


class ArticleSerializer(serializers.ModelSerializer):
    """Format admin (camelCase, comme le reste de l'API d'administration)."""

    titleAr = serializers.CharField(source="title_ar", max_length=200, required=False, allow_blank=True)
    slug = serializers.SlugField(max_length=120, required=False, allow_blank=True)
    excerptAr = serializers.CharField(source="excerpt_ar", max_length=300, required=False, allow_blank=True)
    bodyHtml = serializers.CharField(source="body", required=False, allow_blank=True)
    bodyHtmlAr = serializers.CharField(source="body_ar", required=False, allow_blank=True)
    coverId = serializers.PrimaryKeyRelatedField(
        source="cover", queryset=MediaAsset.objects.all(), required=False, allow_null=True
    )
    coverAlt = serializers.CharField(source="cover_alt", max_length=255, required=False, allow_blank=True)
    publishedAt = serializers.DateTimeField(source="published_at", required=False, allow_null=True)
    cover = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Article
        fields = [
            "id", "title", "titleAr", "slug", "excerpt", "excerptAr", "bodyHtml", "bodyHtmlAr",
            "coverId", "coverAlt", "cover", "status", "publishedAt", "createdAt", "updatedAt",
        ]  # fmt: skip

    def get_cover(self, obj):
        return cover_payload(obj)

    def validate_title(self, value):
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("Le titre est obligatoire.")
        return value

    def validate_slug(self, value):
        if not value:
            return value
        qs = Article.objects.filter(slug=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Cette adresse est déjà utilisée par un autre article.")
        return value

    def validate(self, attrs):
        for key in ("body", "body_ar"):
            if key in attrs:
                attrs[key] = sanitize_html(attrs[key])
        for key in ("excerpt", "excerpt_ar", "title_ar", "cover_alt"):
            if key in attrs:
                attrs[key] = " ".join(attrs[key].split())
        status = attrs.get("status", self.instance.status if self.instance else Article.Status.DRAFT)
        if status == Article.Status.PUBLISHED:
            body = attrs.get("body", self.instance.body if self.instance else "")
            if not body.strip():
                raise serializers.ValidationError({"bodyHtml": ["Le texte est obligatoire pour publier."]})
            # Première publication sans date choisie : maintenant.
            current = self.instance.published_at if self.instance else None
            if not attrs.get("published_at", current):
                attrs["published_at"] = timezone.now()
        return attrs

    def create(self, validated_data):
        validated_data["slug"] = validated_data.get("slug") or unique_slug(validated_data["title"], Article)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "slug" in validated_data and not validated_data["slug"]:
            title = validated_data.get("title", instance.title)
            validated_data["slug"] = unique_slug(title, Article, exclude_pk=instance.pk)
        return super().update(instance, validated_data)
