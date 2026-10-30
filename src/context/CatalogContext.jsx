import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { DATA_SOURCE } from '../config/env.js';
import { fetchProducts, LOCAL_CATALOG } from '../services/productService.js';
import { fetchCategories } from '../services/categoryService.js';
import { fetchStoreConfig } from '../services/configService.js';
import { LOCAL_CATEGORIES } from '../data/local/categories.js';
import { STORE_CONFIG } from '../config/store.js';

const CatalogContext = createContext(null);
const isLocal = DATA_SOURCE === 'local';

/**
 * Catalogue (produits + catégories) et configuration boutique, chargés une seule fois.
 * - Local : disponible immédiatement (aucun écran de chargement, rendu identique).
 * - API   : chargé au démarrage ; écran d'attente puis d'erreur avec « Réessayer ».
 */
export function CatalogProvider({ children }) {
  const [state, setState] = useState(() =>
    isLocal
      ? { status: 'ready', products: LOCAL_CATALOG, categories: LOCAL_CATEGORIES, config: STORE_CONFIG, error: null }
      : { status: 'loading', products: [], categories: [], config: STORE_CONFIG, error: null },
  );
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (isLocal) return undefined;
    const controller = new AbortController();
    setState((s) => ({ ...s, status: 'loading', error: null }));
    const { signal } = controller;
    Promise.all([fetchProducts({ signal }), fetchCategories({ signal }), fetchStoreConfig({ signal })])
      .then(([products, categories, config]) => setState({ status: 'ready', products, categories, config, error: null }))
      .catch((error) => {
        if (!controller.signal.aborted) setState((s) => ({ ...s, status: 'error', error }));
      });
    return () => controller.abort();
  }, [attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  const value = useMemo(() => {
    const byId = new Map(state.products.map((p) => [p.id, p]));
    const labels = Object.fromEntries(state.categories.map((c) => [c.id, c.label]));
    return {
      ...state,
      retry,
      getProductById: (id) => byId.get(id),
      categoryLabel: (id) => labels[id] || id,
    };
  }, [state, retry]);

  return <CatalogContext.Provider value={value}>{children}</CatalogContext.Provider>;
}

export function useCatalog() {
  const ctx = useContext(CatalogContext);
  if (!ctx) throw new Error('useCatalog doit être utilisé dans <CatalogProvider>');
  return ctx;
}
