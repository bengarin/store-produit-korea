/** Lecture/écriture sûres (le navigateur peut bloquer le stockage). */
export function readJSON(storage, key, fallback) {
  try {
    const raw = storage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

export function writeJSON(storage, key, value) {
  try {
    storage.setItem(key, JSON.stringify(value));
  } catch {
    /* stockage indisponible : on ignore */
  }
}

export const safeLocal = () => (typeof window !== 'undefined' ? window.localStorage : null);
export const safeSession = () => (typeof window !== 'undefined' ? window.sessionStorage : null);
