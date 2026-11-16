/** Catégories — Local : src/data/local/categories.js · API : GET /categories */
import { DATA_SOURCE } from '../config/env.js';
import { api } from '../api/client.js';
import { ENDPOINTS } from '../api/endpoints.js';
import { LOCAL_CATEGORIES } from '../data/local/categories.js';

export async function fetchCategories({ signal } = {}) {
  if (DATA_SOURCE === 'local') return LOCAL_CATEGORIES;
  const data = await api.get(ENDPOINTS.categories, { signal });
  return data?.items || data || [];
}

/** Groupes de filtres de la page produits (Admin → Filtres). Mode démo : aucun (rien n'est écrit en dur). */
export async function fetchFilters({ signal } = {}) {
  if (DATA_SOURCE === 'local') return [];
  const data = await api.get(ENDPOINTS.filters, { signal });
  return data?.items || [];
}
