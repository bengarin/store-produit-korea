/**
 * Pixel Meta — une seule intégration pour toute la boutique.
 *
 * Équivalent du code officiel de Meta (même file d'attente `fbq`, même script fbevents.js), mais :
 * - chargé UNE fois, seulement après le consentement du visiteur (jamais dans l'administration ni en mode démo) ;
 * - écrit en module (aucun script en ligne : compatible avec la politique de sécurité du site) ;
 * - le PageView est envoyé à chaque navigation de l'application (voir MetaPixelTracker), pas au chargement ;
 * - si un `fbq` existe déjà (autre intégration), le script n'est pas injecté une seconde fois.
 */
import { META_PIXEL_ID, getConsent, trackingAvailable } from './consent.js';

export const CURRENCY = 'MAD';

// Événements standard de Meta ; les autres partent en « trackCustom » (ex. RemoveFromCart, qui n'est pas standard).
const STANDARD = new Set([
  'PageView', 'ViewContent', 'Search', 'AddToCart', 'AddToWishlist', 'InitiateCheckout', 'AddPaymentInfo', 'Purchase', 'Contact',
]);

let initialised = false;
let granted = false;

function installQueue() {
  // Même amorce que le code officiel : file d'attente jusqu'au chargement de fbevents.js.
  const n = function fbq(...args) {
    if (n.callMethod) n.callMethod(...args);
    else n.queue.push(args);
  };
  window.fbq = n;
  if (!window._fbq) window._fbq = n;
  n.push = n;
  n.loaded = true;
  n.version = '2.0';
  n.queue = [];
  const script = document.createElement('script');
  script.async = true;
  script.src = 'https://connect.facebook.net/en_US/fbevents.js';
  script.dataset.metaPixel = '1';
  document.head.appendChild(script);
}

/** Charge et initialise le pixel (idempotent). Ne fait rien sans consentement. */
export function ensurePixel() {
  if (!trackingAvailable || getConsent() !== 'granted') return false;
  if (typeof window.fbq !== 'function') installQueue();
  if (!granted) {
    window.fbq('consent', 'grant');
    granted = true;
  }
  if (initialised) return true;
  const already = window.fbq.getState?.()?.pixels?.some?.((p) => p.id === META_PIXEL_ID);
  if (!already) window.fbq('init', META_PIXEL_ID);
  initialised = true;
  return true;
}

/** Retrait du consentement : plus aucun envoi (le script déjà chargé reste inactif). */
export function revokePixel() {
  if (typeof window.fbq === 'function' && granted) window.fbq('consent', 'revoke');
  granted = false;
}

let counter = 0;
/** Identifiant d'événement : servira à dédupliquer navigateur + serveur (Conversions API) le jour où elle sera activée. */
export const newEventId = (name) => `${name}.${Date.now().toString(36)}.${(counter += 1).toString(36)}${Math.random().toString(36).slice(2, 6)}`;

/**
 * Envoie un événement. `eventId` : identifiant stable (ex. Purchase = numéro de commande).
 * Retourne l'identifiant envoyé, ou null si rien n'est parti (pas de consentement, démo, aperçu…).
 */
export function track(name, params = {}, eventId = newEventId(name)) {
  if (!ensurePixel()) return null;
  const method = STANDARD.has(name) ? 'track' : 'trackCustom';
  window.fbq(method, name, params, { eventID: eventId });
  if (import.meta.env.DEV) console.debug('[Meta Pixel]', method, name, params, eventId);
  return eventId;
}

// --- Paramètres e-commerce (identifiants et prix réels du catalogue) ---------------------------------

const round2 = (n) => Math.round(n * 100) / 100;

/** Ligne { product, variant?, qty, price } → élément « contents » de Meta. */
const toContent = ({ product, qty, price }) => ({ id: product.id, quantity: qty, item_price: round2(price) });

export function productParams(product, price, qty = 1) {
  return {
    content_ids: [product.id],
    content_type: 'product',
    content_name: product.displayName,
    contents: [{ id: product.id, quantity: qty, item_price: round2(price) }],
    value: round2(price * qty),
    currency: CURRENCY,
  };
}

/** Lignes résolues (utils/pricing.js) → paramètres d'un panier / d'une commande. `value` = montant fourni. */
export function cartParams(lines, value) {
  const ids = [...new Set(lines.map((l) => l.product.id))];
  return {
    content_ids: ids,
    content_type: 'product',
    contents: lines.map(toContent),
    num_items: lines.reduce((sum, l) => sum + l.qty, 0),
    value: round2(value),
    currency: CURRENCY,
  };
}

// --- Achat : une seule fois par commande (même après rechargement ou retour arrière) -----------------

const PURCHASES_KEY = 'mpc.pixel.purchases';

function sentPurchases() {
  try {
    const list = JSON.parse(window.localStorage.getItem(PURCHASES_KEY) || '[]');
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

/**
 * Purchase : uniquement pour une commande RÉELLEMENT créée par le serveur (numéro renvoyé par l'API).
 * Jamais deux fois pour le même numéro (mémorisé dans le navigateur ; event_id = numéro de commande).
 */
export function trackPurchase(order, lines) {
  if (!order?.number || !order?.totals) return null;
  const done = sentPurchases();
  if (done.includes(order.number)) return null;
  const id = track('Purchase', {
    ...cartParams(lines, order.totals.total),
    num_items: order.totals.itemCount,
    order_id: order.number,
  }, `purchase.${order.number}`);
  if (id) {
    try {
      window.localStorage.setItem(PURCHASES_KEY, JSON.stringify([...done, order.number].slice(-50)));
    } catch {
      /* stockage bloqué : la commande est quand même enregistrée côté serveur */
    }
  }
  return id;
}
