import { memo } from 'react';
import { Link } from 'react-router-dom';
import { Heart, ShoppingCart } from 'lucide-react';
import ProductImage from './ProductImage.jsx';
import { formatPrice } from '../utils/currency.js';
import { CATEGORY_LABELS } from '../data/products.js';

function ProductCard({ product, isFavorite, onToggleFavorite, onAdd }) {
  const url = `/produits/${product.id}`;
  return (
    <article className="product-card">
      <button
        className={`fav-btn ${isFavorite ? 'is-active' : ''}`}
        onClick={() => onToggleFavorite(product.id)}
        aria-pressed={isFavorite}
        aria-label={isFavorite ? `Retirer ${product.displayName} des favoris` : `Ajouter ${product.displayName} aux favoris`}
      >
        <Heart size={20} strokeWidth={1.6} />
      </button>
      <Link to={url} className="product-card__media" tabIndex={-1} aria-hidden="true">
        <ProductImage image={product.images[0]} product={product} />
      </Link>
      <div className="product-card__body">
        <p className="product-card__cat">{product.categories.map((c) => CATEGORY_LABELS[c]).join(' · ')}</p>
        <h3 className="product-card__name">
          <Link to={url}>{product.displayName}</Link>
        </h3>
        <p className="product-card__price">{formatPrice(product.price)}</p>
        <div className="product-card__actions">
          <Link to={url} className="btn btn--soft btn--sm">Voir détails</Link>
          <button className="btn btn--primary btn--sm" onClick={() => onAdd(product)}>
            <ShoppingCart size={15} /> Ajouter au panier
          </button>
        </div>
      </div>
    </article>
  );
}

export default memo(ProductCard);
