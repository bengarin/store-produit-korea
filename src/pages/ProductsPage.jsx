import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Heart, SlidersHorizontal, X } from 'lucide-react';
import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import ProductGrid from '../components/ProductGrid.jsx';
import FilterPanel from '../components/FilterPanel.jsx';
import FilterDrawer from '../components/FilterDrawer.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { useCart } from '../context/CartContext.jsx';
import { STORE_CONFIG } from '../config/store.js';
import { getIngredientById } from '../data/ingredients.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { track } from '../analytics/metaPixel.js';
import { activeCount, matches, optionCounts, readFilters, sortProducts, writeFilters } from '../utils/collectionFilters.js';

const EMPTY = { category: 'all', price: null, options: {}, sort: 'recommandes' };

/**
 * Page produits (catalogue, catégorie, résultats de recherche, favoris, ingrédient).
 * Ordinateur : filtres dans une colonne à côté des produits. Mobile : bouton « Filtre » → tiroir.
 * La recherche se fait avec la loupe de l'en-tête (pas de 2e barre ici) ; ses résultats se filtrent comme le reste.
 */
export default function ProductsPage() {
  const [params, setParams] = useSearchParams();
  const { products, filterGroups, allCategories, inCategory, searchProducts } = useCatalog();
  const { favorites } = useCart();
  const { t, tc } = useI18n();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const onlyFavorites = params.get('favoris') === '1';
  const ingredient = getIngredientById(params.get('ingredient'));
  // Listes « sélection » (favoris, ingrédient à l'honneur) : produits seuls, sans filtres ni tri.
  const curated = onlyFavorites || Boolean(ingredient);
  const query = (params.get('q') || '').trim();
  // Filtres affichés immédiatement (état local), puis recopiés dans l'adresse (partage, retour arrière).
  const filtersKey = params.toString();
  const urlFilters = useMemo(() => readFilters(params), [filtersKey]); // eslint-disable-line react-hooks/exhaustive-deps
  const [filters, setFilters] = useState(urlFilters);
  useEffect(() => setFilters(urlFilters), [urlFilters]);

  // Meta Pixel « Search » : une fois par recherche affichée (si le pixel est actif et accepté).
  useEffect(() => {
    if (query) track('Search', { search_string: query.slice(0, 80) });
  }, [query]);

  // Produits avant filtres : recherche (ordre de pertinence), favoris, ingrédient.
  const pool = useMemo(
    () => (query ? searchProducts(query) : products).filter(
      (p) => (!onlyFavorites || favorites.includes(p.id)) && (!ingredient || ingredient.productIds.includes(p.id)),
    ),
    [query, products, searchProducts, onlyFavorites, favorites, ingredient],
  );
  // Bornes du curseur : prix réels du catalogue (arrondis à l'unité).
  const bounds = useMemo(() => {
    const prices = products.map((p) => p.price).filter((n) => Number.isFinite(n));
    return prices.length ? { min: Math.floor(Math.min(...prices)), max: Math.ceil(Math.max(...prices)) } : { min: 0, max: 0 };
  }, [products]);

  const ctx = useMemo(() => ({ inCategory }), [inCategory]);
  const filterFor = useCallback((state) => pool.filter((p) => matches(p, state, ctx)), [pool, ctx]);
  const visible = useMemo(() => sortProducts(filterFor(filters), filters.sort), [filterFor, filters]);

  /** Compteurs affichés à côté de chaque choix, pour un état de filtres donné. */
  const panelProps = useCallback((state) => {
    const base = pool.filter((p) => matches(p, state, { ...ctx, skip: 'category' }));
    const categoryCounts = { all: base.length };
    allCategories.forEach((c) => { categoryCounts[c.id] = base.filter((p) => inCategory(p, c.id)).length; });
    return { bounds, counts: optionCounts(pool, state, filterGroups, ctx), categoryCounts };
  }, [pool, ctx, allCategories, inCategory, bounds, filterGroups]);

  const apply = (state) => {
    setFilters(state);
    setParams(writeFilters(params, state), { replace: true });
  };
  const clearAll = () => {
    setFilters({ ...EMPTY, sort: filters.sort });
    const next = writeFilters(params, { ...EMPTY, sort: filters.sort });
    next.delete('q');
    setParams(next, { replace: true });
  };
  const removeOption = (group, option) => {
    const options = { ...filters.options, [group]: filters.options[group].filter((o) => o !== option) };
    if (!options[group].length) delete options[group];
    apply({ ...filters, options });
  };
  const clearSearch = () => {
    const next = new URLSearchParams(params);
    next.delete('q');
    setParams(next, { replace: true });
  };

  // Puces des filtres actifs (retirables une par une).
  const chips = [];
  if (query) chips.push({ key: 'q', label: `« ${query} »`, remove: clearSearch });
  if (filters.category !== 'all') {
    const cat = allCategories.find((c) => c.id === filters.category);
    chips.push({ key: 'cat', label: cat ? tc(cat.label) : filters.category, remove: () => apply({ ...filters, category: 'all' }) });
  }
  if (filters.price) {
    const unit = t('price.unit');
    const max = Number.isFinite(filters.price.max) ? filters.price.max : bounds.max;
    chips.push({ key: 'price', label: `${filters.price.min} – ${max} ${unit}`, remove: () => apply({ ...filters, price: null }) });
  }
  Object.entries(filters.options).forEach(([g, list]) => {
    const group = filterGroups.find((x) => x.id === g);
    list.forEach((o) => {
      const opt = group?.options.find((x) => x.id === o);
      if (opt) chips.push({ key: `${g}:${o}`, label: tc(opt.label), remove: () => removeOption(g, o) });
    });
  });
  const nActive = activeCount(filters);
  const hasNewest = products.some((p) => p.publishedAt);
  const panel = panelProps(filters);

  let empty = t('price.empty');
  if (!chips.length && onlyFavorites) empty = t('products.emptyFavorites');
  else if (query && chips.length === 1) empty = t('search.empty', { query });

  return (
    <>
      <Header />
      <main className="container section products-page">
        <header className="section-head">
          <p className="eyebrow">{query ? t('search.eyebrow') : onlyFavorites ? t('products.eyebrowFavorites') : ingredient ? t('products.eyebrowIngredient') : t('products.eyebrow')}</p>
          <h1 className="section-title">{query ? t('search.title', { query }) : onlyFavorites ? t('products.titleFavorites') : ingredient ? tc(ingredient.productsTitle) : t('products.title')}</h1>
          <p className="section-intro">
            {query ? t('search.intro')
              : onlyFavorites ? t('products.introFavorites')
              : ingredient ? tc(ingredient.description)
              : t('products.intro', { count: products.length })}
          </p>
        </header>

        {curated ? (
          <CuratedList items={pool} onlyFavorites={onlyFavorites} />
        ) : (
        <div className="collection">
          <aside className="collection__sidebar" aria-label={t('filters.title')}>
            <div className="collection__sidebar-head">
              <h2 className="collection__sidebar-title">{t('filters.title')}</h2>
              {nActive > 0 && <button type="button" className="filter-clear" onClick={clearAll}>{t('filters.clearShort')}</button>}
            </div>
            <FilterPanel {...panel} state={filters} onChange={apply} live />
          </aside>

          <div className="collection__main">
            <div className="collection__toolbar">
              <button type="button" className="collection__filter-btn" onClick={() => setDrawerOpen(true)} aria-haspopup="dialog">
                <SlidersHorizontal size={18} aria-hidden="true" />
                {t('filters.button')}
                {nActive > 0 && <span className="collection__filter-count">{nActive}</span>}
              </button>
              <p className="collection__count" aria-live="polite"><strong>{t('grid.count', { count: visible.length })}</strong></p>
              <label className="collection__sort">
                <span>{t('sort.label')}</span>
                <select value={filters.sort} onChange={(e) => apply({ ...filters, sort: e.target.value })}>
                  <option value="recommandes">{t('sort.recommended')}</option>
                  <option value="prix-asc">{t('sort.priceAsc')}</option>
                  <option value="prix-desc">{t('sort.priceDesc')}</option>
                  {hasNewest && <option value="nouveautes">{t('sort.newest')}</option>}
                </select>
              </label>
            </div>
            {chips.length > 0 && (
              <ul className="collection__chips" aria-label={t('filters.active')}>
                {chips.map((c) => (
                  <li key={c.key}>
                    <button type="button" className="active-chip" onClick={c.remove} aria-label={t('filters.remove', { label: c.label })}>
                      <bdi>{c.label}</bdi><X size={14} aria-hidden="true" />
                    </button>
                  </li>
                ))}
                <li><button type="button" className="filter-clear" onClick={clearAll}>{t('price.clearAll')}</button></li>
              </ul>
            )}
            <ProductGrid items={visible} showCount={false} emptyText={empty}
              emptyAction={chips.length > 0 && <button type="button" className="btn btn--outline" onClick={clearAll}>{t('price.clearAll')}</button>} />
          </div>
        </div>
        )}

        {STORE_CONFIG.showDemoNotices && <p className="demo-note">{t('demo.prices')}</p>}
      </main>
      <SiteFooter />
      {!curated && <FilterDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} applied={filters} empty={EMPTY}
        countFor={(state) => filterFor(state).length} panelProps={panelProps}
        onApply={(state) => { apply(state); setDrawerOpen(false); }} />}
    </>
  );
}

/** Favoris / ingrédient : grille simple. Favoris vides : message centré avec cœur et lien vers le catalogue. */
function CuratedList({ items, onlyFavorites }) {
  const { t } = useI18n();
  if (onlyFavorites && !items.length) {
    return (
      <div className="empty-state favorites-empty">
        <span className="empty-state__icon"><Heart size={30} strokeWidth={1.4} /></span>
        <h2>{t('favorites.emptyTitle')}</h2>
        <p>{t('favorites.emptyText')}</p>
        <Link className="btn btn--primary" to="/produits">{t('favorites.discover')}</Link>
      </div>
    );
  }
  return (
    <div className="curated">
      <p className="grid-count" aria-live="polite">{t('grid.count', { count: items.length })}</p>
      <ProductGrid items={items} showCount={false} />
      {!onlyFavorites && <p className="curated__more"><Link className="btn btn--outline" to="/produits">{t('products.all')}</Link></p>}
    </div>
  );
}
