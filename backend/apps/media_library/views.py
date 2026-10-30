from django.db.models import Q
from rest_framework import generics, status
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.audit.services import log_action
from apps.catalog.permissions import CATALOG_PERMISSION

from .models import MediaAsset
from .processing import ImageRejected
from .serializers import MediaAssetSerializer, MediaUploadSerializer
from .services import create_from_upload, delete_asset


class MediaListCreateView(generics.ListAPIView):
    """GET : médiathèque (recherche ?search=) · POST multipart : téléverser une image."""

    serializer_class = MediaAssetSerializer
    permission_classes = [CATALOG_PERMISSION]
    parser_classes = [MultiPartParser]

    def get_queryset(self):
        qs = MediaAsset.objects.all()
        term = self.request.query_params.get("search", "").strip()
        if term:
            qs = qs.filter(Q(original_filename__icontains=term) | Q(alt__icontains=term))
        return qs

    def post(self, request):
        serializer = MediaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            asset, created = create_from_upload(
                serializer.validated_data["file"],
                alt=serializer.validated_data["alt"],
                user=request.user,
                request=request,
            )
        except ImageRejected as exc:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"file": [str(exc)]}) from exc
        return Response(
            MediaAssetSerializer(asset).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class MediaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MediaAsset.objects.all()
    serializer_class = MediaAssetSerializer
    permission_classes = [CATALOG_PERMISSION]
    parser_classes = [JSONParser]
    http_method_names = ["get", "patch", "delete"]

    def perform_update(self, serializer):
        before = serializer.instance.alt
        asset = serializer.save()
        log_action(
            "media.update",
            actor=self.request.user,
            target=asset,
            changes={"alt": [before, asset.alt]},
            request=self.request,
        )

    def perform_destroy(self, instance):
        delete_asset(instance, user=self.request.user, request=self.request)
