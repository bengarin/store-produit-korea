from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.catalog.permissions import CATALOG_PERMISSION, THEME_PERMISSION, THEME_PUBLISH

from . import services
from .hero_serializers import HeroSlideSerializer
from .models import HeroSlide, ThemeVersion


def _user(u):
    return {"email": u.email, "name": u.full_name or u.email} if u else None


def version_summary(v: ThemeVersion, current_number=None) -> dict:
    return {
        "number": v.number,
        "publishedAt": v.created_at.isoformat(),
        "publishedBy": _user(v.created_by),
        "source": v.source,
        "restoredFrom": v.restored_from.number if v.restored_from_id else None,
        "note": v.note,
        "isCurrent": v.number == current_number,
    }


def theme_state(request) -> dict:
    draft = services.get_draft()
    current = services.latest_version()
    return {
        "draft": {
            "data": draft.data,
            "revision": draft.revision,
            "updatedAt": draft.updated_at.isoformat(),
            "updatedBy": _user(draft.updated_by),
            "basedOn": draft.based_on.number if draft.based_on_id else None,
        },
        "published": version_summary(current, current.number) if current else None,
        "dirty": services.is_dirty(draft),
        "media": services.media_payload(draft.data),
        "canEdit": request.user.role in THEME_PERMISSION.write_roles,
        "canPublish": request.user.role in THEME_PUBLISH,
    }


def require_publisher(request):
    if request.user.role not in THEME_PUBLISH:
        raise PermissionDenied("Seuls le Propriétaire et l'Administrateur peuvent publier ou restaurer le thème.")


class ThemeView(APIView):
    """GET /admin/theme : brouillon, version publiée, état (modifié ou non), images, droits."""

    permission_classes = [THEME_PERMISSION]

    def get(self, request):
        return Response(theme_state(request))


class DraftSerializer(serializers.Serializer):
    data = serializers.JSONField()
    revision = serializers.IntegerField(min_value=0)


class DraftView(APIView):
    """PUT /admin/theme/draft {data, revision} — enregistre le brouillon (jamais visible des visiteurs)."""

    permission_classes = [THEME_PERMISSION]

    def put(self, request):
        s = DraftSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.save_draft(
            s.validated_data["data"], revision=s.validated_data["revision"], user=request.user, request=request
        )
        return Response(theme_state(request))


class PublishSerializer(serializers.Serializer):
    revision = serializers.IntegerField(min_value=0)
    note = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class PublishView(APIView):
    """POST /admin/theme/publish {revision, note} — publie EXACTEMENT la révision affichée (Propriétaire, Admin)."""

    permission_classes = [THEME_PERMISSION]

    def post(self, request):
        require_publisher(request)
        s = PublishSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        version = services.publish(
            revision=s.validated_data["revision"], note=s.validated_data["note"], user=request.user, request=request
        )
        return Response({**theme_state(request), "publishedNumber": version.number}, status=status.HTTP_201_CREATED)


class VersionListView(APIView):
    permission_classes = [THEME_PERMISSION]

    def get(self, request):
        current = services.latest_version()
        number = current.number if current else None
        versions = ThemeVersion.objects.select_related("created_by", "restored_from").order_by("-number")[:100]
        return Response({"items": [version_summary(v, number) for v in versions]})


class VersionDetailView(APIView):
    permission_classes = [THEME_PERMISSION]

    def get(self, request, number):
        v = get_object_or_404(ThemeVersion, number=number)
        return Response({**version_summary(v), "data": v.data, "media": services.media_payload(v.data)})


class RestoreView(APIView):
    """POST /admin/theme/versions/{n}/restore — republie la version n (Propriétaire, Admin)."""

    permission_classes = [THEME_PERMISSION]

    def post(self, request, number):
        require_publisher(request)
        version = get_object_or_404(ThemeVersion, number=number)
        new = services.restore(version, user=request.user, request=request)
        return Response({**theme_state(request), "publishedNumber": new.number}, status=status.HTTP_201_CREATED)


class LoadView(APIView):
    """POST /admin/theme/versions/{n}/load {revision} — copie la version n dans le brouillon (sans publier)."""

    permission_classes = [THEME_PERMISSION]

    def post(self, request, number):
        version = get_object_or_404(ThemeVersion, number=number)
        s = DraftSerializer(data={"data": {}, **request.data})
        s.is_valid(raise_exception=True)
        services.load_into_draft(version, revision=s.validated_data["revision"], user=request.user, request=request)
        return Response(theme_state(request))


class PublicThemeView(APIView):
    """GET /api/v1/store/theme — dernière version PUBLIÉE (jamais le brouillon) ; null = thème par défaut du site."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        response = Response(services.public_theme_payload())
        response["Cache-Control"] = "no-cache"
        return response


# --- Bannière d'accueil : diapositives (Admin → Visuels marketing) ----------------------------------------
class HeroSlideListCreateView(APIView):
    """GET : toutes les diapositives (publiées ou non) · POST : nouvelle diapositive (ajoutée à la fin)."""

    permission_classes = [CATALOG_PERMISSION]

    def get(self, request):
        qs = HeroSlide.objects.select_related("desktop_media", "mobile_media")
        return Response({"items": HeroSlideSerializer(qs, many=True).data})

    @transaction.atomic
    def post(self, request):
        serializer = HeroSlideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        last = HeroSlide.objects.select_for_update().order_by("-position").values_list("position", flat=True).first()
        slide = serializer.save(position=0 if last is None else last + 1)
        log_action(
            "hero.slide_add", actor=request.user, target=slide, changes={"title": slide.title_fr}, request=request
        )
        return Response(HeroSlideSerializer(slide).data, status=status.HTTP_201_CREATED)


class HeroSlideReorderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False, max_length=50)


class HeroSlideReorderView(APIView):
    """POST {ids} : nouvel ordre (TOUTES les diapositives, chacune une fois)."""

    permission_classes = [CATALOG_PERMISSION]

    @transaction.atomic
    def post(self, request):
        data = HeroSlideReorderSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        ids = data.validated_data["ids"]
        existing = set(HeroSlide.objects.select_for_update().values_list("pk", flat=True))
        if len(set(ids)) != len(ids) or set(ids) != existing:
            raise serializers.ValidationError({"ids": ["Liste invalide : rechargez la page et réessayez."]})
        for position, slide_id in enumerate(ids):
            HeroSlide.objects.filter(pk=slide_id).update(position=position)
        log_action(
            "hero.slide_reorder",
            actor=request.user,
            target_type="themes.heroslide",
            changes={"order": ids},
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class HeroSlideDetailView(APIView):
    """PATCH : modifier / publier / dépublier · DELETE : supprimer (les images restent dans la médiathèque)."""

    permission_classes = [CATALOG_PERMISSION]

    def patch(self, request, pk):
        slide = get_object_or_404(HeroSlide, pk=pk)
        serializer = HeroSlideSerializer(slide, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        before = slide.is_active
        slide = serializer.save()
        changes = {"fields": sorted(request.data.keys())[:30]}
        if before != slide.is_active:
            changes["isActive"] = [before, slide.is_active]
        log_action("hero.slide_update", actor=request.user, target=slide, changes=changes, request=request)
        return Response(HeroSlideSerializer(slide).data)

    def delete(self, request, pk):
        slide = get_object_or_404(HeroSlide, pk=pk)
        slide_id, title = slide.pk, slide.title_fr
        slide.delete()
        log_action(
            "hero.slide_delete",
            actor=request.user,
            target_type="themes.heroslide",
            target_id=slide_id,
            changes={"title": title},
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
