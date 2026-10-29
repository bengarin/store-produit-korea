import { API_BASE_URL, API_TIMEOUT_MS } from '../config/env.js';

/** Erreur HTTP normalisée (status 0 = réseau / délai dépassé). */
export class ApiError extends Error {
  constructor(message, { status = 0, data = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Client HTTP minimal basé sur fetch (aucune dépendance).
 * - JSON en entrée / sortie
 * - délai maximal (AbortController)
 * - erreurs homogènes (ApiError)
 */
export async function request(path, { method = 'GET', body, signal, headers = {} } = {}) {
  if (!API_BASE_URL) throw new ApiError('API non configurée (VITE_API_BASE_URL manquant)');

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  signal?.addEventListener('abort', () => controller.abort(), { once: true });

  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}), ...headers },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    const isJson = res.headers.get('content-type')?.includes('application/json');
    const data = isJson ? await res.json() : null;
    if (!res.ok) throw new ApiError(data?.message || `Erreur ${res.status}`, { status: res.status, data });
    return data;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err.name === 'AbortError') throw new ApiError('Le serveur ne répond pas (délai dépassé)');
    throw new ApiError('Connexion au serveur impossible');
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  get: (path, opts) => request(path, { ...opts, method: 'GET' }),
  post: (path, body, opts) => request(path, { ...opts, method: 'POST', body }),
};
