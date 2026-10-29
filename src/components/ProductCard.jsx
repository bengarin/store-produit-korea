import { memo, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Heart, ShoppingCart, Check } from 'lucide-react';
import ProductImage from './ProductImage.jsx';
import useReveal from '../hooks/useReveal.js';
import { formatPrice } from '../utils/currency.js';
import { CATEGORY_LABELS } from '../data/products.js';

function ProductCard({ product, index = 0, isFavorite, onToggleFavorite, onAdd }) {
  const url = `/produits/${product.id}`;
  const [revealRef, visible] = useReveal();
  const [added, setAdded] = useState(false);
  const timer = useRef();
  useEffect(() => () => clearTimeout(timer.current), []);

  const handleAdd = () => {
    onAdd(product);
    setAdded(true);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setAdded(false), 1400);
  };

  return (
    <article
      ref={revealRef}
      className={`product-card reveal ${visible ? 'is-visible' : ''}`}
      style={{ '--reveal-delay': `${Math.min(index, 5) * 80}ms` }}
    >
      <button
        className={`fav-btn ${isFavorite ? 'is-active' : ''}`}
        onClick={() => onToggleFavorite(product.id)}
        aria-pressed={isFavorite}
        aria-label={isFavorite ? `Retirer ${product.displayName} des favoris` : `Ajouter ${product.displayName} aux favoris`}
      >
        <Heart size={19} strokeWidth={1.6} />
      </button>
      <Link to={url} className="product-card__media" tabIndex={-1} aria-hidden="true">
        <ProductImage image={product.cardImage} />
      </Link>
      <div className="product-card__body">
        <p className="product-card__cat">{product.categories.map((c) => CATEGORY_LABELS[c]).join(' · ')}</p>
        <h3 className="product-card__name">
          <Link to={url}>{product.displayName}</Link>
        </h3>
        <p className="product-card__line">{product.cardLine}</p>
        <p className="product-card__price">{formatPrice(product.price)}</p>
        <div className="product-card__actions">
          <Link to={url} className="btn btn--soft">Voir détails</Link>
          <button
            className={`btn btn--primary ${added ? 'is-added' : ''}`}
            onClick={handleAdd}
            aria-label={`Ajouter ${product.displayName} au panier`}
          >
            {added ? <Check size={17} aria-hidden="true" /> : <ShoppingCart size={17} aria-hidden="true" />}
            <span>{added ? 'Ajouté' : 'Ajouter au panier'}</span>
          </button>
        </div>
      </div>
    </article>
  );
}

export default memo(ProductCard);
