/**
 * Commandes.
 * - API  : POST /orders → le backend valide, recalcule les totaux, enregistre et renvoie le numéro.
 * - Local: SIMULATION (aucune commande n'est transmise) — clairement signalée à l'écran.
 */
import { DATA_SOURCE } from '../config/env.js';
import { api } from '../api/client.js';
import { ENDPOINTS } from '../api/endpoints.js';
import { STORE_CONFIG } from '../config/store.js';
import { readJSON, writeJSON, safeSession } from '../utils/storage.js';
import { STORAGE_KEYS } from './storageKeys.js';

/** true tant que les commandes ne sont pas réellement transmises. */
export const ORDERS_ARE_SIMULATED = DATA_SOURCE === 'local';

/** Corps envoyé au backend : uniquement des identifiants et quantités (pas de prix de confiance). */
export function buildOrderRequest({ customer, lines, promoCode }) {
  return {
    customer,
    items: lines.map(({ product, qty }) => ({ productId: product.id, qty })),
    promoCode: promoCode || null,
    paymentMethod: 'cod',
    deliveryMethod: 'home',
  };
}

function localOrderNumber() {
  const rand = String(Math.floor(Math.random() * 100000)).padStart(5, '0');
  return `NAT${new Date().getFullYear()}-${rand}`;
}

/**
 * Envoie la commande. Retourne l'objet affiché sur la page de confirmation.
 * `preview` = lignes et totaux calculés côté navigateur (affichage en mode local).
 */
export async function submitOrder({ customer, lines, promoCode, totals }) {
  const request = buildOrderRequest({ customer, lines, promoCode });
  const summary = {
    customer,
    lines: lines.map(({ product, qty }) => ({ id: product.id, name: product.displayName, price: product.price, qty })),
    promoCode: totals.discount > 0 ? promoCode : '',
    payment: 'cod',
    delivery: 'home',
  };

  if (DATA_SOURCE === 'api') {
    const res = await api.post(ENDPOINTS.orders, request);
    return { ...summary, number: res.number, createdAt: res.createdAt, totals: res.totals || totals };
  }

  await new Promise((r) => setTimeout(r, 900)); // simulation d'envoi
  return { ...summary, number: localOrderNumber(), createdAt: new Date().toISOString(), totals };
}

// --- Achat direct (« Commander maintenant ») : gardé hors du panier ---
export const saveDirectOrder = (item) => writeJSON(safeSession(), STORAGE_KEYS.directOrder, item);
export const loadDirectOrder = () => readJSON(safeSession(), STORAGE_KEYS.directOrder, null);
export const clearDirectOrder = () => safeSession()?.removeItem(STORAGE_KEYS.directOrder);

// --- Dernière commande (page de confirmation, survit au rechargement) ---
export const saveLastOrder = (order) => writeJSON(safeSession(), STORAGE_KEYS.lastOrder, order);
export const loadLastOrder = () => readJSON(safeSession(), STORAGE_KEYS.lastOrder, null);

export function buildWhatsAppLink(orderNumber, config = STORE_CONFIG) {
  const number = (config.whatsappNumber || '').replace(/\D/g, '');
  if (!number) return null;
  return `https://wa.me/${number}?text=${encodeURIComponent(`Bonjour, je souhaite suivre ma commande ${orderNumber}.`)}`;
}
