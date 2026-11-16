import { useMemo } from 'react';
import ProductCard from './ProductCard.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { useCart } from '../context/CartContext.jsx';
import useQuickAdd from '../hooks/useQuickAdd.js';
import { useI18n } from '../i18n/I18nContext.jsx';

/** Filtres catégories (pilules) */
export function CategoryChips({ value, onChange, extra = null }) {
  const { categories } = useCatalog();
  const { t, tc } = useI18n();
  const options = [{ id: 'all', label: t('grid.all') }, ...categories.map((c) => ({ ...c, label: tc(c.label) }))];
  return (
    <div className="chips" role="group" aria-label={t('grid.filter')}>
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
export default function ProductGrid({ category = 'all', onlyFavorites = false, ids = null, query = '', price = null, emptyText, emptyAction = null }) {
  const { products, inCategory, searchProducts } = useCatalog();
  const { favorites, toggleFavorite } = useCart();
  const handleAdd = useQuickAdd();
  const { t } = useI18n();

  const visible = useMemo(
    () =>
      (query ? searchProducts(query) : products).filter(
        (p) =>
          (category === 'all' || inCategory(p, category)) &&
          (!onlyFavorites || favorites.includes(p.id)) &&
          (!ids || ids.includes(p.id)) &&
          (!price || (p.price >= price.min && p.price <= price.max)),
      ),
    [products, category, onlyFavorites, ids, query, price, favorites, inCategory, searchProducts],
  );

  return (
    <>
      <p className="grid-count" aria-live="polite">
        {t('grid.count', { count: visible.length })}
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
        <div className="empty-inline">
          <p>{emptyText || t('grid.empty')}</p>
          {emptyAction}
        </div>
      )}
    </>
  );
}
