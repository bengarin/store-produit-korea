/**
 * Produits — seul point d'accès au catalogue.
 * Local : src/data/local/products.js (+ photos) · API : GET /products
 */
import { DATA_SOURCE } from '../config/env.js';
import { api } from '../api/client.js';
import { ENDPOINTS } from '../api/endpoints.js';
import { LOCAL_PRODUCTS } from '../data/local/products.js';
import { PRODUCT_IMAGES } from '../data/local/productImages.js';

/**
 * Forme unique utilisée par l'interface, quelle que soit la source.
 * Les clés d'images (cardImage, mainImage, galleryImages, image, sceneImage, hoverImage)
 * viennent du dossier local ou, plus tard, des URL renvoyées par l'API.
 */
export function normalizeProduct(raw, images = {}) {
  const gallery = images.galleryImages || raw.images || [];
  const main = images.mainImage || gallery[0] || null;
  return {
    id: raw.id,
    slug: raw.slug || raw.id,
    brand: raw.brand,
    name: raw.name,
    displayName: raw.displayName || `${raw.brand} ${raw.name}`,
    cardLine: raw.cardLine || '',
    price: Number(raw.price),
    categories: raw.categories || [],
    summary: raw.summary || '',
    highlights: raw.highlights || [],
    ingredients: raw.ingredients || [],
    usage: raw.usage || [],
    benefits: raw.benefits || [],
    skinTypes: raw.skinTypes || '',
    stock: raw.stock ?? null, // inconnu en local
    cardImage: images.cardImage || main,
    mainImage: main,
    galleryImages: gallery,
    image: images.image || main,
    sceneImage: images.sceneImage || main,
    hoverImage: images.hoverImage || null,
  };
}

/** Catalogue local normalisé, disponible immédiatement (sans réseau). */
export const LOCAL_CATALOG = LOCAL_PRODUCTS.map((p) => normalizeProduct(p, PRODUCT_IMAGES[p.id]));

export async function fetchProducts({ signal } = {}) {
  if (DATA_SOURCE === 'local') return LOCAL_CATALOG;
  const data = await api.get(ENDPOINTS.products, { signal });
  return (data?.items || data || []).map((p) => normalizeProduct(p, p));
}
