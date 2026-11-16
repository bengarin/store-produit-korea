/**
 * Blog et avis sur la boutique — API : GET /blog, GET /blog/:slug, GET/POST /reviews.
 * Mode démo (sans serveur) : aucun article ni avis (rien n'est inventé) et le formulaire d'avis est désactivé.
 */
import { DATA_SOURCE } from '../config/env.js';
import { api } from '../api/client.js';
import { ENDPOINTS } from '../api/endpoints.js';

export const CONTENT_AVAILABLE = DATA_SOURCE === 'api';

/** Texte de l'article dans la langue demandée (champ arabe vide = texte français). */
export function localizeArticle(article, lang) {
  const tr = lang === 'ar' ? article.translations?.ar || {} : {};
  return { ...article, title: tr.title || article.title, excerpt: tr.excerpt || article.excerpt, bodyHtml: tr.bodyHtml || article.bodyHtml };
}

export async function fetchArticles({ signal } = {}) {
  if (!CONTENT_AVAILABLE) return [];
  const data = await api.get(ENDPOINTS.blog, { signal });
  return data?.items || [];
}

export async function fetchArticle(slug, { signal } = {}) {
  if (!CONTENT_AVAILABLE) return null;
  return api.get(ENDPOINTS.blogArticle(slug), { signal });
}

export async function fetchReviews({ signal } = {}) {
  if (!CONTENT_AVAILABLE) return { count: 0, average: null, items: [] };
  return api.get(ENDPOINTS.reviews, { signal });
}

export function submitReview(payload) {
  return api.post(ENDPOINTS.reviews, payload);
}
