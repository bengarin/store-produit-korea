import { STORE_CONFIG } from '../config/store.js';
import { getProductById } from '../data/products.js';
import { readJSON, writeJSON, safeSession } from './storage.js';

const DIRECT_KEY = 'nature.directOrder';
const LAST_ORDER_KEY = 'nature.lastOrder';

const round2 = (n) => Math.round(n * 100) / 100;

/** [{id, qty}] → lignes enrichies avec le produit (les produits inconnus sont ignorés). */
export function resolveLines(items) {
  return items
    .map(({ id, qty }) => {
      const product = getProductById(id);
      return product ? { product, qty, lineTotal: product.price * qty } : null;
    })
    .filter(Boolean);
}

/** Fusionne deux listes {id, qty} en additionnant les quantités. */
export function mergeItems(a, b) {
  const map = new Map();
  [...a, ...b].forEach(({ id, qty }) => map.set(id, (map.get(id) || 0) + qty));
  return [...map].map(([id, qty]) => ({ id, qty }));
}

export function getPromoPercent(code) {
  if (!code) return 0;
  return STORE_CONFIG.promoCodes[code.trim().toUpperCase()] || 0;
}

export function computeTotals(lines, promoCode) {
  const itemCount = lines.reduce((s, l) => s + l.qty, 0);
  const subtotal = round2(lines.reduce((s, l) => s + l.lineTotal, 0));
  const discount = round2((subtotal * getPromoPercent(promoCode)) / 100);
  const { deliveryFee, freeDeliveryThreshold } = STORE_CONFIG;
  const freeDelivery = freeDeliveryThreshold != null && subtotal >= freeDeliveryThreshold;
  const delivery = itemCount === 0 || freeDelivery ? 0 : deliveryFee;
  const total = round2(subtotal - discount + delivery);
  return { itemCount, subtotal, discount, delivery, total };
}

/** Numéro de commande local, ex. NAT2026-48213 (généré dans le navigateur). */
export function generateOrderNumber() {
  const year = new Date().getFullYear();
  const rand = String(Math.floor(Math.random() * 100000)).padStart(5, '0');
  return `NAT${year}-${rand}`;
}

/** Téléphone marocain : 05/06/07 + 8 chiffres, ou +212 / 00212. */
export function normalizeMoroccanPhone(input) {
  const cleaned = (input || '').replace(/[\s.\-()]/g, '');
  const match = cleaned.match(/^(?:\+212|00212|212|0)([5-7]\d{8})$/);
  return match ? `+212${match[1]}` : null;
}

// --- Achat direct ("Commander maintenant") : gardé hors du panier ---
export const saveDirectOrder = (item) => writeJSON(safeSession(), DIRECT_KEY, item);
export const loadDirectOrder = () => readJSON(safeSession(), DIRECT_KEY, null);
export const clearDirectOrder = () => safeSession()?.removeItem(DIRECT_KEY);

// --- Dernière commande (pour la page de confirmation, survit au rechargement) ---
export const saveLastOrder = (order) => writeJSON(safeSession(), LAST_ORDER_KEY, order);
export const loadLastOrder = () => readJSON(safeSession(), LAST_ORDER_KEY, null);

export function buildWhatsAppLink(orderNumber) {
  const number = (STORE_CONFIG.whatsappNumber || '').replace(/\D/g, '');
  if (!number) return null;
  const text = `Bonjour, je souhaite suivre ma commande ${orderNumber}.`;
  return `https://wa.me/${number}?text=${encodeURIComponent(text)}`;
}
