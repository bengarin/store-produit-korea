import { useMemo } from 'react';
import ProductCard from './ProductCard.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { useCart } from '../context/CartContext.jsx';
import useQuickAdd from '../hooks/useQuickAdd.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { relatedProducts } from '../utils/related.js';

/** « Vous aimerez aussi » : autres produits du catalogue, mêmes cartes que la page Catalogue. */
export default function RelatedProducts({ product }) {
  const { products } = useCatalog();
  const { favorites, toggleFavorite } = useCart();
  const handleAdd = useQuickAdd();
  const { t } = useI18n();
  const list = useMemo(() => relatedProducts(products, product), [products, product]);
  if (!list.length) return null;

  return (
    <section className="related" aria-labelledby="related-title">
      <div className="container">
        <header className="section-head related__head">
          <h2 className="section-title related__title" id="related-title">{t('related.title')}</h2>
          <p className="section-intro">{t('related.intro')}</p>
        </header>
        <div className="product-grid product-grid--related">
          {list.map((p, i) => (
            <ProductCard key={p.id} product={p} index={i} linked
              isFavorite={favorites.includes(p.id)} onToggleFavorite={toggleFavorite} onAdd={handleAdd} />
          ))}
        </div>
      </div>
    </section>
  );
}
