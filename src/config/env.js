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

/**
 * API d'administration (même domaine, session + CSRF). Par défaut déduite de VITE_API_BASE_URL
 * (`/api/v1/store` → `/api/v1/admin`) ; peut être fixée seule avec VITE_ADMIN_API_BASE_URL
 * (ex. pour gérer le stock pendant que la boutique publique reste en mode démo).
 */
const rawAdmin = (import.meta.env.VITE_ADMIN_API_BASE_URL || '').trim();
const derivedAdmin = API_BASE_URL.endsWith('/store') ? `${API_BASE_URL.slice(0, -'/store'.length)}/admin` : '';
export const ADMIN_API_BASE_URL = (rawAdmin || derivedAdmin).replace(/\/+$/, '');

/** Délai maximal d'une requête API (ms). */
export const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS) || 10000;
