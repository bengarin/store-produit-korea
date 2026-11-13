import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Search, X } from 'lucide-react';
import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import ProductGrid, { CategoryChips } from '../components/ProductGrid.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { STORE_CONFIG } from '../config/store.js';
import { getIngredientById } from '../data/ingredients.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { track } from '../analytics/metaPixel.js';

export default function ProductsPage() {
  const [params, setParams] = useSearchParams();
  const { products, categoryTree, topCategory } = useCatalog();
  const { t, tc } = useI18n();
  const category = params.get('categorie') || 'all';
  const onlyFavorites = params.get('favoris') === '1';
  const ingredient = getIngredientById(params.get('ingredient'));
  const query = (params.get('q') || '').trim();
  const [draft, setDraft] = useState(query);
  useEffect(() => setDraft(query), [query]);
  // Meta Pixel « Search » : une fois par recherche affichée (si le pixel est actif et accepté).
  useEffect(() => {
    if (query) track('Search', { search_string: query.slice(0, 80) });
  }, [query]);

  const applySearch = (e) => {
    e.preventDefault();
    const next = new URLSearchParams(params);
    const value = draft.trim();
    if (value) next.set('q', value);
    else next.delete('q');
    setParams(next);
  };
  const clearSearch = () => {
    const next = new URLSearchParams(params);
    next.delete('q');
    setParams(next, { replace: true });
  };

  // Catégorie choisie (ou parente de la sous-catégorie choisie) : ses sous-catégories en 2e ligne de filtres.
  const parent = category === 'all' ? null : categoryTree.find((c) => c.id === topCategory(category));
  const subcategories = parent?.children || [];

  const selectCategory = (id) => {
    const next = new URLSearchParams(params);
    if (id === 'all') next.delete('categorie');
    else next.set('categorie', id);
    setParams(next, { replace: true });
  };

  return (
    <>
      <Header />
      <main className="container section products-page">
        <header className="section-head">
          <p className="eyebrow">{query ? t('search.eyebrow') : onlyFavorites ? t('products.eyebrowFavorites') : ingredient ? t('products.eyebrowIngredient') : t('products.eyebrow')}</p>
          <h1 className="section-title">{query ? t('search.title', { query }) : onlyFavorites ? t('products.titleFavorites') : ingredient ? tc(ingredient.productsTitle) : t('products.title')}</h1>
          <p className="section-intro">
            {query
              ? t('search.intro')
              : onlyFavorites
              ? t('products.introFavorites')
              : ingredient
                ? tc(ingredient.description)
                : t('products.intro', { count: products.length })}
          </p>
          <form className="page-search" role="search" onSubmit={applySearch}>
            <Search size={19} strokeWidth={1.7} aria-hidden="true" className="page-search__icon" />
            <input type="search" className="page-search__input" value={draft} onChange={(e) => setDraft(e.target.value)}
              placeholder={t('search.placeholder')} aria-label={t('search.label')} enterKeyHint="search" maxLength={80} />
            {query && (
              <button type="button" className="icon-btn icon-btn--sm" onClick={clearSearch} aria-label={t('search.clear')}>
                <X size={18} />
              </button>
            )}
            <button type="submit" className="page-search__submit">{t('search.submit')}</button>
          </form>
          <CategoryChips
            value={category === 'all' ? 'all' : topCategory(category)}
            onChange={selectCategory}
            extra={(onlyFavorites || ingredient) && <Link className="chip chip--link" to="/produits">{t('products.all')}</Link>}
          />
          {subcategories.length > 0 && (
            <div className="chips chips--sub" role="group" aria-label={t('nav.toggleSub', { label: tc(parent.label) })}>
              {[{ id: parent.id, label: t('nav.allInCategory', { label: tc(parent.label) }) }, ...subcategories.map((c) => ({ ...c, label: tc(c.label) }))].map((c) => (
                <button key={c.id} type="button" className={`chip chip--sub ${category === c.id ? 'is-active' : ''}`}
                  aria-pressed={category === c.id} onClick={() => selectCategory(c.id)}>
                  {c.label}
                </button>
              ))}
            </div>
          )}
        </header>
        <ProductGrid
          category={category}
          onlyFavorites={onlyFavorites}
          ids={ingredient ? ingredient.productIds : null}
          query={query}
          emptyText={query ? t('search.empty', { query }) : onlyFavorites ? t('products.emptyFavorites') : undefined}
        />
        {STORE_CONFIG.showDemoNotices && (
          <p className="demo-note">{t('demo.prices')}</p>
        )}
      </main>
      <SiteFooter />
    </>
  );
}
