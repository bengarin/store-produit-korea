from rest_framework import serializers

from .models import MediaAsset


class MediaAssetSerializer(serializers.ModelSerializer):
    url = serializers.CharField(read_only=True)
    url640 = serializers.CharField(source="url_640", read_only=True)
    originalFilename = serializers.CharField(source="original_filename", read_only=True)
    mimeType = serializers.CharField(source="mime_type", read_only=True)
    sizeBytes = serializers.IntegerField(source="size_bytes", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = MediaAsset
        fields = [
            "id",
            "url",
            "url640",
            "alt",
            "width",
            "height",
            "mimeType",
            "sizeBytes",
            "originalFilename",
            "source",
            "createdAt",
        ]
        read_only_fields = ["width", "height", "source"]


class MediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=False, max_length=255)
    alt = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
