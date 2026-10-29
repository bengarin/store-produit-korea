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
