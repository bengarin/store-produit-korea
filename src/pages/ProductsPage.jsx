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
  const { products } = useCatalog();
  const { t, tc } = useI18n();
  const category = params.get('categorie') || 'all';
  const onlyFavorites = params.get('favoris') === '1';
  const ingredient = getIngredientById(params.get('ingredient'));

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
            value={category}
            onChange={selectCategory}
            extra={(onlyFavorites || ingredient) && <Link className="chip chip--link" to="/produits">{t('products.all')}</Link>}
          />
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
