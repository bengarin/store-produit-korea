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
    const tree = buildCategoryTree(categories);
    const parentOf = Object.fromEntries(categories.filter((c) => c.parent).map((c) => [c.id, c.parent]));
    const familyOf = Object.fromEntries(tree.map((c) => [c.id, new Set([c.id, ...c.children.map((x) => x.id)])]));
    return {
      ...state,
      products,
      // `categories` = catégories principales (pilules, filtres) ; `categoryTree` = menu avec sous-catégories.
      categories: tree,
      categoryTree: tree,
      allCategories: categories,
      retry,
      getProductById: (id) => byId.get(id),
      categoryLabel: (id) => labels[id] || id,
      /** Catégorie principale d'une catégorie ou sous-catégorie (elle-même si principale). */
      topCategory: (id) => parentOf[id] || id,
      /** Le produit est-il dans cette catégorie, ou dans l'une de ses sous-catégories ? */
      inCategory: (product, id) => {
        const family = familyOf[id] || new Set([id]);
        return product.categories.some((c) => family.has(c));
      },
    };
  }, [state, products, categories, retry]);

  return <CatalogContext.Provider value={value}>{children}</CatalogContext.Provider>;
}

/**
 * Catégories principales, chacune avec ses sous-catégories (`children`), dans l'ordre reçu de l'API.
 * Une sous-catégorie dont la catégorie est absente (masquée) n'apparaît pas.
 */
export function buildCategoryTree(categories) {
  const tops = categories.filter((c) => !c.parent).map((c) => ({ ...c, children: [] }));
  const byId = new Map(tops.map((c) => [c.id, c]));
  categories.forEach((c) => {
    if (c.parent) byId.get(c.parent)?.children.push(c);
  });
  return tops;
}

export function useCatalog() {
  const ctx = useContext(CatalogContext);
  if (!ctx) throw new Error('useCatalog doit être utilisé dans <CatalogProvider>');
  return ctx;
}
