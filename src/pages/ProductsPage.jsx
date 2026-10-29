import { Link, useSearchParams } from 'react-router-dom';
import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import ProductGrid, { CategoryChips } from '../components/ProductGrid.jsx';
import { PRODUCTS, CATALOG_IS_PLACEHOLDER } from '../data/products.js';

export default function ProductsPage() {
  const [params, setParams] = useSearchParams();
  const category = params.get('categorie') || 'all';
  const onlyFavorites = params.get('favoris') === '1';

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
        <div className="section-head">
          <div>
            <p className="eyebrow">{onlyFavorites ? 'Votre sélection' : 'Notre collection'}</p>
            <h1 className="section-title">{onlyFavorites ? 'Mes favoris' : 'Nos produits'}</h1>
            <p className="section-intro">
              {onlyFavorites
                ? 'Les soins que vous avez mis de côté.'
                : `Découvrez nos ${PRODUCTS.length} soins essentiels pour une peau saine et éclatante.`}
            </p>
          </div>
          <CategoryChips
            value={category}
            onChange={selectCategory}
            extra={onlyFavorites && <Link className="chip chip--link" to="/produits">Tout le catalogue</Link>}
          />
        </div>
        <ProductGrid
          category={category}
          onlyFavorites={onlyFavorites}
          emptyText={onlyFavorites ? 'Aucun favori pour le moment. Touchez le ♡ d’un produit pour l’ajouter.' : undefined}
        />
        {CATALOG_IS_PLACEHOLDER && (
          <p className="demo-note">Prix provisoires — à confirmer avant la mise en ligne.</p>
        )}
      </main>
      <SiteFooter />
    </>
  );
}
