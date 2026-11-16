/**
 * Configuration boutique (livraison, villes, WhatsApp…).
 * Local : src/config/store.js · API : GET /config
 * ⚠️ Les codes promo ne doivent PAS être exposés par l'API publique :
 *    côté backend, valider via POST /promo-codes/validate.
 */
import { DATA_SOURCE } from '../config/env.js';
import { api } from '../api/client.js';
import { ENDPOINTS } from '../api/endpoints.js';
import { STORE_CONFIG } from '../config/store.js';

export async function fetchStoreConfig({ signal } = {}) {
  if (DATA_SOURCE === 'local') return STORE_CONFIG;
  return mergeStoreConfig(await api.get(ENDPOINTS.config, { signal }));
}

/** Config publique du serveur (API ou données de démarrage) fusionnée avec les valeurs par défaut. */
export function mergeStoreConfig(remote) {
  // Les codes promo ne viennent JAMAIS de la config publique : ils sont vérifiés par POST /promo-codes/validate.
  return { ...STORE_CONFIG, ...remote, promoCodes: {} };
}
