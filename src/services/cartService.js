/**
 * Panier — persistance navigateur (localStorage).
 * Un panier « invité » reste côté navigateur même avec un backend ;
 * seul le contenu final est envoyé à la commande (POST /orders).
 */
import { readJSON, writeJSON, safeLocal } from '../utils/storage.js';
import { STORAGE_KEYS } from './storageKeys.js';

export const MAX_QTY = 20;
export const clampQty = (q) => Math.max(1, Math.min(MAX_QTY, Math.floor(q) || 1));

/** Ligne de panier : `variantId` seulement s'il est connu (mode API) — le mode démo garde { id, qty }. */
export function toItem(id, qty, variantId) {
  return Number.isInteger(variantId) && variantId > 0 ? { id, variantId, qty: clampQty(qty) } : { id, qty: clampQty(qty) };
}

export function loadCart() {
  const raw = readJSON(safeLocal(), STORAGE_KEYS.cart, []);
  return Array.isArray(raw)
    ? raw.filter((i) => i && typeof i.id === 'string').map((i) => toItem(i.id, i.qty, i.variantId))
    : [];
}
export const saveCart = (items) => writeJSON(safeLocal(), STORAGE_KEYS.cart, items);

/**
 * Code promo appliqué : { code, type, value, minSubtotal } ou null.
 * (Ancien format : simple chaîne « NATURE10 », relu puis converti par CartContext.)
 */
export function loadPromo() {
  const raw = readJSON(safeLocal(), STORAGE_KEYS.promo, null);
  if (typeof raw === 'string') return raw ? { code: raw, legacy: true } : null;
  return raw && typeof raw.code === 'string' && typeof raw.type === 'string' ? raw : null;
}
export const savePromo = (promo) => writeJSON(safeLocal(), STORAGE_KEYS.promo, promo);
