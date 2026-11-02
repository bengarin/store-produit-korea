import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { DATA_SOURCE } from '../config/env.js';
import { fetchProducts, LOCAL_CATALOG, localizeCategory, localizeProduct } from '../services/productService.js';
import { useI18n } from '../i18n/I18nContext.jsx';
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
  const { lang } = useI18n();

  // Catalogue dans la langue active : textes saisis en arabe dans l'administration, sinon français.
  const products = useMemo(() => state.products.map((p) => localizeProduct(p, lang)), [state.products, lang]);
  const categories = useMemo(() => state.categories.map((c) => localizeCategory(c, lang)), [state.categories, lang]);

  const value = useMemo(() => {
    const byId = new Map(products.map((p) => [p.id, p]));
    const labels = Object.fromEntries(categories.map((c) => [c.id, c.label]));
    return {
      ...state,
      products,
      categories,
      retry,
      getProductById: (id) => byId.get(id),
      categoryLabel: (id) => labels[id] || id,
    };
  }, [state, products, categories, retry]);

  return <CatalogContext.Provider value={value}>{children}</CatalogContext.Provider>;
}

export function useCatalog() {
  const ctx = useContext(CatalogContext);
  if (!ctx) throw new Error('useCatalog doit être utilisé dans <CatalogProvider>');
  return ctx;
}
