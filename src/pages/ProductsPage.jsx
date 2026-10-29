import { useCallback, useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import Header from '../components/Header.jsx';
import ProductCard from '../components/ProductCard.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import { CATEGORIES, PRODUCTS, CATALOG_IS_PLACEHOLDER } from '../data/products.js';
import { useCart } from '../context/CartContext.jsx';
import { useToast } from '../context/ToastContext.jsx';

export default function ProductsPage() {
  const [params, setParams] = useSearchParams();
  const category = params.get('categorie') || 'all';
  const onlyFavorites = params.get('favoris') === '1';
  const { addItem, favorites, toggleFavorite } = useCart();
  const showToast = useToast();

  const visible = useMemo(
    () =>
      PRODUCTS.filter(
        (p) =>
          (category === 'all' || p.categories.includes(category)) &&
          (!onlyFavorites || favorites.includes(p.id)),
      ),
    [category, onlyFavorites, favorites],
  );

  const handleAdd = useCallback(
    (product) => {
      addItem(product.id, 1);
      showToast(`${product.displayName} ajouté au panier`);
    },
    [addItem, showToast],
  );

  const selectCategory = (id) => {
    const next = new URLSearchParams(params);
    if (id === 'all') next.delete('categorie');
    else next.set('categorie', id);
    setParams(next, { replace: true });
  };

  return (
    <>
      <Header />
      <main className="container products-page">
        <h1 className="page-title">{onlyFavorites ? 'Mes favoris' : 'Nos produits'}</h1>
        <p className="page-intro">
          {onlyFavorites
            ? 'Les soins que vous avez mis de côté.'
            : `Découvrez nos ${PRODUCTS.length} soins essentiels pour une peau saine et éclatante.`}
        </p>

        <div className="chips" role="group" aria-label="Filtrer par catégorie">
          {CATEGORIES.map((c) => (
            <button
              key={c.id}
              className={`chip ${category === c.id ? 'is-active' : ''}`}
              aria-pressed={category === c.id}
              onClick={() => selectCategory(c.id)}
            >
              {c.label}
            </button>
          ))}
          {onlyFavorites && (
            <Link className="chip chip--link" to="/produits">Voir tout le catalogue</Link>
          )}
        </div>

        {visible.length ? (
          <div className="product-grid">
            {visible.map((p) => (
              <ProductCard
                key={p.id}
                product={p}
                isFavorite={favorites.includes(p.id)}
                onToggleFavorite={toggleFavorite}
                onAdd={handleAdd}
              />
            ))}
          </div>
        ) : (
          <p className="empty-inline">
            {onlyFavorites ? 'Aucun favori pour le moment. Touchez le ♡ d’un produit pour l’ajouter.' : 'Aucun produit dans cette catégorie.'}
          </p>
        )}

        {CATALOG_IS_PLACEHOLDER && (
          <p className="demo-note">Visuels et prix provisoires — à remplacer par les photos et tarifs officiels.</p>
        )}
      </main>
      <SiteFooter />
    </>
  );
}
