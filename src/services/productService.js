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
const toNumberOrNull = (value) => (value == null || value === '' || Number.isNaN(Number(value)) ? null : Number(value));

function normalizeVariant(v) {
  return {
    id: v.id,
    title: v.title || '',
    sku: v.sku || '',
    price: Number(v.price),
    compareAtPrice: toNumberOrNull(v.compareAtPrice),
    available: v.available === true,
    // Ancien format sans `availability` : non disponible = « Indisponible » (jamais supposé en stock).
    availability: v.availability || (v.available === true ? 'available' : 'unavailable'),
    isDefault: Boolean(v.isDefault),
    options: v.options || {},
    image: v.image || null,
  };
}

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
    descriptionHtml: raw.descriptionHtml || '',
    highlights: raw.highlights || [],
    ingredients: raw.ingredients || [],
    usage: raw.usage || [],
    benefits: raw.benefits || [],
    skinTypes: raw.skinTypes || '',
    stock: raw.stock ?? null, // inconnu en local
    // Variantes et prix barré (mode API). Mode démo : aucune variante, produit disponible, pas de prix barré.
    compareAtPrice: toNumberOrNull(raw.compareAtPrice),
    inStock: raw.inStock !== false,
    options: (raw.options || []).filter((o) => o && o.name && Array.isArray(o.values)),
    variants: (raw.variants || []).map(normalizeVariant),
    cardImage: images.cardImage || main,
    mainImage: main,
    galleryImages: gallery,
    image: images.image || main,
    sceneImage: images.sceneImage || main,
    hoverImage: images.hoverImage || null,
    // Contenus traduits saisis dans l'administration (mode API) : { ar: { displayName, summary, … } }.
    translations: raw.translations || {},
    // Visuels marketing (colonne de droite de la fiche), distincts des photos du produit.
    marketing: Array.isArray(raw.marketing) ? raw.marketing : [],
  };
}

const TRANSLATABLE = ['displayName', 'cardLine', 'summary', 'descriptionHtml', 'ingredients', 'usage', 'benefits', 'skinTypes'];
const filled = (v) => (Array.isArray(v) ? v.length > 0 : Boolean(v));

/**
 * Produit dans la langue demandée : chaque champ traduit remplace le français, un champ non traduit reste en français.
 * `nameFr` garde le nom d'origine (mesure d'audience, commandes).
 */
export function localizeProduct(product, lang) {
  const tr = product.translations?.[lang];
  if (lang === 'fr' || !tr) return product;
  const out = { ...product, nameFr: product.displayName };
  TRANSLATABLE.forEach((key) => { if (filled(tr[key])) out[key] = tr[key]; });
  if (Array.isArray(tr.highlights)) {
    out.highlights = product.highlights.map((h, i) => (tr.highlights[i] ? { ...h, label: tr.highlights[i] } : h));
  }
  return out;
}

/** Catégorie dans la langue demandée (libellé traduit s'il existe). */
export const localizeCategory = (category, lang) => {
  const label = category.translations?.[lang]?.label;
  return lang !== 'fr' && label ? { ...category, label } : category;
};

/** Catalogue local normalisé, disponible immédiatement (sans réseau). */
export const LOCAL_CATALOG = LOCAL_PRODUCTS.map((p) => normalizeProduct(p, PRODUCT_IMAGES[p.id]));

export async function fetchProducts({ signal } = {}) {
  if (DATA_SOURCE === 'local') return LOCAL_CATALOG;
  const data = await api.get(ENDPOINTS.products, { signal });
  return (data?.items || data || []).map((p) => normalizeProduct(p, p));
}

/**
 * Visuels marketing à afficher dans la langue demandée :
 * - arabe : visuels arabes + sans texte ; si le produit n'a AUCUN visuel arabe, visuels français + sans texte ;
 * - français : visuels français + sans texte.
 */
export function marketingFor(product, lang) {
  const list = product.marketing || [];
  const wanted = lang === 'ar' && list.some((m) => m.language === 'ar') ? 'ar' : 'fr';
  return list.filter((m) => m.language === wanted || m.language === 'any');
}
