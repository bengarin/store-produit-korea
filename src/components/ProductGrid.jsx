import { useMemo } from 'react';
import ProductCard from './ProductCard.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { useCart } from '../context/CartContext.jsx';
import useQuickAdd from '../hooks/useQuickAdd.js';
import { useI18n } from '../i18n/I18nContext.jsx';

/**
 * Grille produits. `items` fourni : liste déjà filtrée et triée (page produits) ; sinon filtres simples ci-dessous.
 * `showCount` : affiche « N produits » au-dessus (la page produits l'affiche dans sa barre d'outils).
 */
export default function ProductGrid({ category = 'all', onlyFavorites = false, ids = null, query = '', price = null, items = null, showCount = true, emptyText, emptyAction = null }) {
  const { products, inCategory, searchProducts } = useCatalog();
  const { favorites, toggleFavorite } = useCart();
  const handleAdd = useQuickAdd();
  const { t } = useI18n();

  const visible = useMemo(
    () => items || (query ? searchProducts(query) : products).filter(
        (p) =>
          (category === 'all' || inCategory(p, category)) &&
          (!onlyFavorites || favorites.includes(p.id)) &&
          (!ids || ids.includes(p.id)) &&
          (!price || (p.price >= price.min && p.price <= price.max)),
      ),
    [items, products, category, onlyFavorites, ids, query, price, favorites, inCategory, searchProducts],
  );

  return (
    <>
      {showCount && (
        <p className="grid-count" aria-live="polite">
          {t('grid.count', { count: visible.length })}
        </p>
      )}
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
