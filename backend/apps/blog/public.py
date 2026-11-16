"""Articles visibles dans la boutique et leur format JSON public."""

from django.utils import timezone

from .models import Article


def published_articles():
    return Article.objects.filter(status=Article.Status.PUBLISHED, published_at__lte=timezone.now()).select_related(
        "cover"
    )


def cover_payload(article):
    if not article.cover_id:
        return None
    data = {"src": article.cover.url, "alt": article.cover_alt or article.cover.alt or article.title}
    if article.cover.file_640:
        data["src640"] = article.cover.url_640
    return data


def article_payload(article, *, full=False):
    data = {
        "slug": article.slug,
        "title": article.title,
        "excerpt": article.excerpt,
        "publishedAt": article.published_at.isoformat() if article.published_at else None,
        "cover": cover_payload(article),
    }
    ar = {k: v for k, v in (("title", article.title_ar), ("excerpt", article.excerpt_ar)) if v}
    if full:
        data["bodyHtml"] = article.body
        if article.body_ar:
            ar["bodyHtml"] = article.body_ar
    data["translations"] = {"ar": ar} if ar else {}
    return data
