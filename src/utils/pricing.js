/**
 * Calculs de prix côté navigateur (AFFICHAGE uniquement).
 * ⚠️ Le serveur recalcule tout à la commande (prix, remise, livraison) et ne lit jamais ces montants.
 */
import { STORE_CONFIG } from '../config/store.js';
import { findVariant, lineKey, unitPrice, variantLabel, variantStatus } from './variants.js';

const round2 = (n) => Math.round(n * 100) / 100;

/**
 * [{id, variantId?, qty}] → lignes enrichies : produit, variante, prix unitaire, libellé, disponibilité.
 * Les produits ou variantes inconnus du catalogue sont ignorés.
 */
export function resolveLines(items, getProductById) {
  return items
    .map((item) => {
      const product = getProductById(item.id);
      const variant = product && findVariant(product, item.variantId);
      if (!product || variant === undefined) return null;
      const price = unitPrice(product, variant);
      return {
        key: lineKey(item),
        product,
        variant,
        qty: item.qty,
        price,
        label: variantLabel(product, variant),
        status: variantStatus(product, variant),
        lineTotal: price * item.qty,
      };
    })
    .filter(Boolean);
}

/** Fusionne deux listes {id, variantId?, qty} en additionnant les quantités d'une même ligne. */
export function mergeItems(a, b) {
  const map = new Map();
  [...a, ...b].forEach((item) => {
    const key = lineKey(item);
    const prev = map.get(key);
    map.set(key, prev ? { ...prev, qty: prev.qty + item.qty } : { ...item });
  });
  return [...map.values()];
}

/**
 * Mode démo local : code → remise décrite comme celle renvoyée par l'API
 * ({ code, type, value, minSubtotal }) ; null si le code n'existe pas.
 */
export function resolveLocalPromo(code, config = STORE_CONFIG) {
  const normalized = (code || '').trim().toUpperCase();
  const percent = (config.promoCodes || {})[normalized];
  return percent ? { code: normalized, type: 'percentage', value: percent, minSubtotal: null } : null;
}

/** `promo` = { code, type: 'percentage' | 'fixed_amount' | 'free_shipping', value, minSubtotal } ou null. */
export function computeTotals(lines, promo, config = STORE_CONFIG) {
  const itemCount = lines.reduce((s, l) => s + l.qty, 0);
  const subtotal = round2(lines.reduce((s, l) => s + l.lineTotal, 0));
  const eligible = promo && (promo.minSubtotal == null || subtotal >= promo.minSubtotal);
  let discount = 0;
  if (eligible && promo.type === 'percentage') discount = round2((subtotal * promo.value) / 100);
  if (eligible && promo.type === 'fixed_amount') discount = Math.min(round2(promo.value), subtotal);
  const freeDelivery =
    (eligible && promo.type === 'free_shipping') ||
    (config.freeDeliveryThreshold != null && subtotal >= config.freeDeliveryThreshold);
  const delivery = itemCount === 0 || freeDelivery ? 0 : config.deliveryFee;
  const total = round2(subtotal - discount + delivery);
  return { itemCount, subtotal, discount, delivery, total };
}
