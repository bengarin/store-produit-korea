import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { DATA_SOURCE } from '../config/env.js';
import { fetchProducts, LOCAL_CATALOG, localizeCategory, localizeCollection, localizeProduct, normalizeProducts } from '../services/productService.js';
import { bootstrapData } from '../services/bootstrap.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { fetchCategories, fetchCollections, fetchFilters } from '../services/categoryService.js';
import { fetchStoreConfig, mergeStoreConfig } from '../services/configService.js';
import { indexProduct, searchEntries } from '../utils/search.js';
import { LOCAL_CATEGORIES } from '../data/local/categories.js';
import { STORE_CONFIG } from '../config/store.js';

const CatalogContext = createContext(null);
const isLocal = DATA_SOURCE === 'local';

/**
 * Catalogue (produits + catégories) et configuration boutique, chargés une seule fois.
 * - Local : disponible immédiatement (aucun écran de chargement, rendu identique).
 * - API   : chargé au démarrage ; écran d'attente puis d'erreur avec « Réessayer ».
 */
/** Données jointes par le serveur à la page : catalogue prêt dès le premier rendu (aucun appel réseau). */
function bootState() {
  const boot = isLocal ? null : bootstrapData();
  if (!boot?.products || !boot.categories || !boot.config) return null;
  return {
    status: 'ready',
    products: normalizeProducts(boot.products),
    categories: boot.categories,
    filters: boot.filters || [],
    collections: boot.collections || [],
    config: mergeStoreConfig(boot.config),
    error: null,
  };
}

export function CatalogProvider({ children }) {
  const [state, setState] = useState(() => {
    if (isLocal) return { status: 'ready', products: LOCAL_CATALOG, categories: LOCAL_CATEGORIES, filters: [], collections: [], config: STORE_CONFIG, error: null };
    return bootState() || { status: 'loading', products: [], categories: [], filters: [], collections: [], config: STORE_CONFIG, error: null };
  });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    // Mode démo, ou catalogue déjà fourni par la page (1er chargement) : rien à télécharger.
    if (isLocal || (attempt === 0 && state.status === 'ready')) return undefined;
    const controller = new AbortController();
    setState((s) => ({ ...s, status: 'loading', error: null }));
    const { signal } = controller;
    // Filtres : facultatifs (un échec n'empêche pas la boutique de s'afficher, la page produits garde le prix).
    const filters = fetchFilters({ signal }).catch(() => []);
    const collections = fetchCollections({ signal }).catch(() => []); // facultatives, comme les filtres
    Promise.all([fetchProducts({ signal }), fetchCategories({ signal }), fetchStoreConfig({ signal }), filters, collections])
      .then(([products, categories, config, filterGroups, collectionList]) => setState({
        status: 'ready', products, categories, filters: filterGroups, collections: collectionList, config, error: null,
      }))
      .catch((error) => {
        if (!controller.signal.aborted) setState((s) => ({ ...s, status: 'error', error }));
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- l'état initial ne sert qu'au 1er passage
  }, [attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  const { lang } = useI18n();

  // Catalogue dans la langue active : textes saisis en arabe dans l'administration, sinon français.
  const products = useMemo(() => state.products.map((p) => localizeProduct(p, lang)), [state.products, lang]);
  const categories = useMemo(() => state.categories.map((c) => localizeCategory(c, lang)), [state.categories, lang]);
  // Groupes de filtres et leurs valeurs, libellés dans la langue active (arabe vide = français).
  const filterGroups = useMemo(
    () => state.filters.map((g) => ({ ...localizeCategory(g, lang), options: g.options.map((o) => localizeCategory(o, lang)) })),
    [state.filters, lang],
  );

  // Collections (Admin → Collections) dans la langue active.
  const collections = useMemo(() => state.collections.map((c) => localizeCollection(c, lang)), [state.collections, lang]);

  // Index de recherche : textes français et arabes du produit + libellés de ses catégories (toutes langues).
  const searchIndex = useMemo(() => {
    const catLabels = new Map(state.categories.map((c) => [c.id, [c.label, ...Object.values(c.translations || {}).map((t) => t?.label)]]));
    const parentOf = new Map(state.categories.filter((c) => c.parent).map((c) => [c.id, c.parent]));
    return state.products.map((raw) => {
      const ids = new Set(raw.categories.flatMap((id) => [id, parentOf.get(id)]).filter(Boolean));
      return { id: raw.id, index: indexProduct(raw, [...ids].flatMap((id) => catLabels.get(id) || [])) };
    });
  }, [state.products, state.categories]);

  const value = useMemo(() => {
    const byId = new Map(products.map((p) => [p.id, p]));
    const entries = searchIndex.map((e) => ({ product: byId.get(e.id), index: e.index })).filter((e) => e.product);
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
      filterGroups,
      collections,
      getCollection: (id) => collections.find((c) => c.id === id),
      retry,
      getProductById: (id) => byId.get(id),
      /** Produits correspondant à une recherche (FR ou AR), les plus pertinents d'abord. */
      searchProducts: (query) => searchEntries(entries, query),
      categoryLabel: (id) => labels[id] || id,
      /** Catégorie principale d'une catégorie ou sous-catégorie (elle-même si principale). */
      topCategory: (id) => parentOf[id] || id,
      /** Le produit est-il dans cette catégorie, ou dans l'une de ses sous-catégories ? */
      inCategory: (product, id) => {
        const family = familyOf[id] || new Set([id]);
        return product.categories.some((c) => family.has(c));
      },
    };
  }, [state, products, categories, filterGroups, collections, searchIndex, retry]);

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
