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
  return { ...STORE_CONFIG, ...(await api.get(ENDPOINTS.config, { signal })) };
}
