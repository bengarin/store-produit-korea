import { Link, useSearchParams } from 'react-router-dom';
import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import ProductGrid, { CategoryChips } from '../components/ProductGrid.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { STORE_CONFIG } from '../config/store.js';
import { getIngredientById } from '../data/ingredients.js';
import { useI18n } from '../i18n/I18nContext.jsx';

export default function ProductsPage() {
  const [params, setParams] = useSearchParams();
  const { products, categoryTree, topCategory } = useCatalog();
  const { t, tc } = useI18n();
  const category = params.get('categorie') || 'all';
  const onlyFavorites = params.get('favoris') === '1';
  const ingredient = getIngredientById(params.get('ingredient'));

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
          <p className="eyebrow">{onlyFavorites ? t('products.eyebrowFavorites') : ingredient ? t('products.eyebrowIngredient') : t('products.eyebrow')}</p>
          <h1 className="section-title">{onlyFavorites ? t('products.titleFavorites') : ingredient ? tc(ingredient.productsTitle) : t('products.title')}</h1>
          <p className="section-intro">
            {onlyFavorites
              ? t('products.introFavorites')
              : ingredient
                ? tc(ingredient.description)
                : t('products.intro', { count: products.length })}
          </p>
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
          emptyText={onlyFavorites ? t('products.emptyFavorites') : undefined}
        />
        {STORE_CONFIG.showDemoNotices && (
          <p className="demo-note">{t('demo.prices')}</p>
        )}
      </main>
      <SiteFooter />
    </>
  );
}
