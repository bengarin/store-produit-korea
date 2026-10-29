/**
 * Variables d'environnement (Vite expose uniquement celles préfixées par VITE_).
 * ⚠️ Tout ce qui est ici est PUBLIC (visible dans le navigateur) : jamais de secret.
 */
const rawBase = (import.meta.env.VITE_API_BASE_URL || '').trim();

/** URL de base de l'API REST, sans « / » final. Vide = pas de backend. */
export const API_BASE_URL = rawBase.replace(/\/+$/, '');

/**
 * Source des données :
 *  - 'local' : données embarquées dans src/data/local (situation actuelle)
 *  - 'api'   : API REST à l'adresse API_BASE_URL
 */
export const DATA_SOURCE = API_BASE_URL ? 'api' : 'local';

/** Délai maximal d'une requête API (ms). */
export const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS) || 10000;
