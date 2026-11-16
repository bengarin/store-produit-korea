from django.db.models import Q
from django.http import Http404
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_action

from .models import Article
from .permissions import BLOG_PERMISSION
from .public import article_payload, published_articles
from .serializers import ArticleSerializer


# --- Boutique ------------------------------------------------------------------
class PublicArticleListView(APIView):
    """GET /api/v1/store/blog — articles publiés, du plus récent au plus ancien (sans le texte complet)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"items": [article_payload(a) for a in published_articles()[:100]]})


class PublicArticleDetailView(APIView):
    """GET /api/v1/store/blog/<slug> — article publié complet ; brouillon ou inconnu : 404."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug):
        article = published_articles().filter(slug=slug).first()
        if article is None:
            raise Http404
        return Response(article_payload(article, full=True))


# --- Administration ------------------------------------------------------------
class ArticleListCreateView(generics.ListCreateAPIView):
    """GET (?status=draft|published, ?search=) · POST : nouvel article (brouillon par défaut)."""

    serializer_class = ArticleSerializer
    permission_classes = [BLOG_PERMISSION]

    def get_queryset(self):
        qs = Article.objects.select_related("cover").order_by("-updated_at", "-id")
        params = self.request.query_params
        if params.get("status") in Article.Status.values:
            qs = qs.filter(status=params["status"])
        term = params.get("search", "").strip()
        if term:
            qs = qs.filter(Q(title__icontains=term) | Q(title_ar__icontains=term) | Q(slug__icontains=term))
        return qs

    def perform_create(self, serializer):
        article = serializer.save(author=self.request.user)
        log_action(
            "blog.create", actor=self.request.user, target=article, changes={"status": article.status},
            request=self.request,
        )  # fmt: skip


class ArticleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Article.objects.select_related("cover")
    serializer_class = ArticleSerializer
    permission_classes = [BLOG_PERMISSION]
    http_method_names = ["get", "patch", "delete"]

    def perform_update(self, serializer):
        before = serializer.instance.status
        article = serializer.save()
        log_action(
            "blog.update", actor=self.request.user, target=article, changes={"status": [before, article.status]},
            request=self.request,
        )  # fmt: skip

    def perform_destroy(self, instance):
        log_action(
            "blog.delete", actor=self.request.user, target=instance, changes={"title": instance.title},
            request=self.request,
        )  # fmt: skip
        instance.delete()
