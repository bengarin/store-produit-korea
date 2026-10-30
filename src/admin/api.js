/**
 * Client de l'API d'administration : session Django (cookie HttpOnly) + jeton CSRF.
 * Le serveur reste l'unique autorité (droits, calculs, stock) : ce fichier ne fait que transporter.
 */
import { ADMIN_API_BASE_URL, API_TIMEOUT_MS } from '../config/env.js';

export const ADMIN_API_READY = Boolean(ADMIN_API_BASE_URL);

export class AdminApiError extends Error {
  constructor(message, { status = 0, code = 'network_error', fields = null, items = null } = {}) {
    super(message);
    this.name = 'AdminApiError';
    this.status = status;
    this.code = code;
    this.fields = fields;
    this.items = items;
  }

  /** Premier message lisible d'un champ (ex. err.fieldMessage('quantity')). */
  fieldMessage(name) {
    const value = this.fields?.[name];
    return Array.isArray(value) ? value[0] : typeof value === 'string' ? value : null;
  }
}

let onUnauthenticated = null;
/** Appelé quand la session a expiré (le contexte d'authentification redirige vers la connexion). */
export function setUnauthenticatedHandler(fn) {
  onUnauthenticated = fn;
}

function csrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)mpc_csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : '';
}

/** URL absolue d'une ressource admin (liens : facture, export Excel). */
export function adminUrl(path, params = {}) {
  const url = new URL(`${ADMIN_API_BASE_URL}${path}`, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value);
  });
  return url.toString();
}

export async function adminRequest(path, { method = 'GET', body, params, signal, formData } = {}) {
  if (!ADMIN_API_READY) throw new AdminApiError('API d’administration non configurée.', { code: 'not_configured' });
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  signal?.addEventListener('abort', () => controller.abort(), { once: true });
  const unsafe = !['GET', 'HEAD', 'OPTIONS'].includes(method);
  try {
    const res = await fetch(adminUrl(path, params), {
      method,
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json',
        ...(body !== undefined && !formData ? { 'Content-Type': 'application/json' } : {}),
        ...(unsafe ? { 'X-CSRFToken': csrfToken() } : {}),
      },
      body: formData || (body !== undefined ? JSON.stringify(body) : undefined),
      signal: controller.signal,
    });
    if (res.status === 204) return null;
    const isJson = res.headers.get('content-type')?.includes('application/json');
    const data = isJson ? await res.json() : null;
    if (!res.ok) {
      const error = data?.error || {};
      const code = error.code || `http_${res.status}`;
      if (res.status === 401 || code === 'not_authenticated') onUnauthenticated?.();
      throw new AdminApiError(error.message || `Erreur ${res.status}`, {
        status: res.status, code, fields: error.fields || null, items: error.items || null,
      });
    }
    return data;
  } catch (err) {
    if (err instanceof AdminApiError) throw err;
    if (signal?.aborted) throw err;
    if (err.name === 'AbortError') throw new AdminApiError('Le serveur ne répond pas (délai dépassé).');
    throw new AdminApiError('Connexion au serveur impossible.');
  } finally {
    clearTimeout(timer);
  }
}

export const admin = {
  get: (path, params, opts) => adminRequest(path, { ...opts, params }),
  post: (path, body) => adminRequest(path, { method: 'POST', body: body ?? {} }),
  patch: (path, body) => adminRequest(path, { method: 'PATCH', body }),
  put: (path, body) => adminRequest(path, { method: 'PUT', body }),
  del: (path) => adminRequest(path, { method: 'DELETE' }),
  /** Envoi de fichier (multipart) : le navigateur fixe lui-même l'en-tête Content-Type. */
  upload: (path, formData) => adminRequest(path, { method: 'POST', formData }),
};
