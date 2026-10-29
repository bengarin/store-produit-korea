/**
 * Panier — persistance navigateur (localStorage).
 * Un panier « invité » reste côté navigateur même avec un backend ;
 * seul le contenu final est envoyé à la commande (POST /orders).
 */
import { readJSON, writeJSON, safeLocal } from '../utils/storage.js';
import { STORAGE_KEYS } from './storageKeys.js';

export const MAX_QTY = 20;
export const clampQty = (q) => Math.max(1, Math.min(MAX_QTY, Math.floor(q) || 1));

export function loadCart() {
  const raw = readJSON(safeLocal(), STORAGE_KEYS.cart, []);
  return Array.isArray(raw) ? raw.filter((i) => i && typeof i.id === 'string').map((i) => ({ id: i.id, qty: clampQty(i.qty) })) : [];
}
export const saveCart = (items) => writeJSON(safeLocal(), STORAGE_KEYS.cart, items);

export const loadPromoCode = () => readJSON(safeLocal(), STORAGE_KEYS.promo, '');
export const savePromoCode = (code) => writeJSON(safeLocal(), STORAGE_KEYS.promo, code);
