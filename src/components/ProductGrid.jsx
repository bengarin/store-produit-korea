import { useCallback, useMemo } from 'react';
import ProductCard from './ProductCard.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { useCart } from '../context/CartContext.jsx';
import { useToast } from '../context/ToastContext.jsx';

/** Filtres catégories (pilules) */
export function CategoryChips({ value, onChange, extra = null }) {
  const { categories } = useCatalog();
  const options = [{ id: 'all', label: 'Tous' }, ...categories];
  return (
    <div className="chips" role="group" aria-label="Filtrer par catégorie">
      {options.map((c) => (
        <button
          key={c.id}
          className={`chip ${value === c.id ? 'is-active' : ''}`}
          aria-pressed={value === c.id}
          onClick={() => onChange(c.id)}
        >
          {c.label}
        </button>
      ))}
      {extra}
    </div>
  );
}

/** Grille produits filtrée + ajout au panier avec toast. */
export default function ProductGrid({ category = 'all', onlyFavorites = false, ids = null, emptyText }) {
  const { products } = useCatalog();
  const { addItem, favorites, toggleFavorite } = useCart();
  const showToast = useToast();

  const visible = useMemo(
    () =>
      products.filter(
        (p) =>
          (category === 'all' || p.categories.includes(category)) &&
          (!onlyFavorites || favorites.includes(p.id)) &&
          (!ids || ids.includes(p.id)),
      ),
    [products, category, onlyFavorites, ids, favorites],
  );

  const handleAdd = useCallback(
    (product) => {
      addItem(product.id, 1);
      showToast(`${product.displayName} ajouté au panier`);
    },
    [addItem, showToast],
  );

  return (
    <>
      <p className="grid-count" aria-live="polite">
        {visible.length} produit{visible.length > 1 ? 's' : ''}
      </p>
      {visible.length ? (
        <div className="product-grid">
          {visible.map((p, i) => (
            <ProductCard
              key={p.id}
              product={p}
              index={i}
              isFavorite={favorites.includes(p.id)}
              onToggleFavorite={toggleFavorite}
              onAdd={handleAdd}
            />
          ))}
        </div>
      ) : (
        <p className="empty-inline">{emptyText || 'Aucun produit dans cette catégorie.'}</p>
      )}
    </>
  );
}
