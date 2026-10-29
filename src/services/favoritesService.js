/**
 * Favoris — stockés dans le navigateur.
 * Avec un backend, la synchronisation nécessitera un compte client (non prévu ici :
 * aucune authentification fictive n'est mise en place).
 */
import { readJSON, writeJSON, safeLocal } from '../utils/storage.js';
import { STORAGE_KEYS } from './storageKeys.js';

export function loadFavorites() {
  const raw = readJSON(safeLocal(), STORAGE_KEYS.favorites, []);
  return Array.isArray(raw) ? raw.filter((id) => typeof id === 'string') : [];
}
export const saveFavorites = (ids) => writeJSON(safeLocal(), STORAGE_KEYS.favorites, ids);
