/**
 * Calculs de prix côté navigateur (affichage uniquement).
 * ⚠️ Le backend devra RECALCULER prix, remise et livraison à partir de ses propres
 *    données : ces valeurs ne doivent jamais être prises telles quelles depuis le client.
 */
import { STORE_CONFIG } from '../config/store.js';

const round2 = (n) => Math.round(n * 100) / 100;

/** [{id, qty}] → lignes enrichies (les produits inconnus du catalogue sont ignorés). */
export function resolveLines(items, getProductById) {
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

/** Remise (%) d'un code promo — version locale de démonstration (backend : POST /promo-codes/validate). */
export function getPromoPercent(code) {
  if (!code) return 0;
  return STORE_CONFIG.promoCodes[code.trim().toUpperCase()] || 0;
}

export function computeTotals(lines, promoCode, config = STORE_CONFIG) {
  const itemCount = lines.reduce((s, l) => s + l.qty, 0);
  const subtotal = round2(lines.reduce((s, l) => s + l.lineTotal, 0));
  const discount = round2((subtotal * getPromoPercent(promoCode)) / 100);
  const freeDelivery = config.freeDeliveryThreshold != null && subtotal >= config.freeDeliveryThreshold;
  const delivery = itemCount === 0 || freeDelivery ? 0 : config.deliveryFee;
  const total = round2(subtotal - discount + delivery);
  return { itemCount, subtotal, discount, delivery, total };
}
