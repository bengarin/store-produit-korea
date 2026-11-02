import { memo, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Heart, ShoppingCart, Check, Leaf } from 'lucide-react';
import ProductImage from './ProductImage.jsx';
import useReveal from '../hooks/useReveal.js';
import { formatPrice } from '../utils/currency.js';
import { useCatalog } from '../context/CatalogContext.jsx';
import { compareAtPrice, hasChoice, productStatus } from '../utils/variants.js';
import { useI18n } from '../i18n/I18nContext.jsx';

function ProductCard({ product, index = 0, isFavorite, onToggleFavorite, onAdd, animate = true, variant = 'default' }) {
  const { categoryLabel } = useCatalog();
  const { t, tc, autoDir } = useI18n();
  const scene = variant === 'scene';
  const url = `/produits/${product.id}`;
  const [revealRef, visible] = useReveal();
  const [added, setAdded] = useState(false);
  const timer = useRef();
  useEffect(() => () => clearTimeout(timer.current), []);

  const status = productStatus(product);
  const canBuy = status === 'available';
  const choice = hasChoice(product);
  const compare = compareAtPrice(product, null);
  const statusLabel = canBuy ? '' : t(`status.${status}`);
  const name = product.displayName;

  const handleAdd = () => {
    if (onAdd(product) === false) return; // fiche ouverte pour choisir une option, ou produit indisponible
    setAdded(true);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setAdded(false), 1400);
  };

  return (
    <article
      ref={revealRef}
      className={`product-card ${scene ? 'product-card--scene' : ''} ${animate ? `reveal ${visible ? 'is-visible' : ''}` : 'is-visible'}`}
      style={animate ? { '--reveal-delay': `${Math.min(index, 5) * 80}ms` } : undefined}
    >
      <button
        className={`fav-btn ${isFavorite ? 'is-active' : ''}`}
        onClick={() => onToggleFavorite(product.id)}
        aria-pressed={isFavorite}
        aria-label={isFavorite ? t('card.favRemove', { name }) : t('card.favAdd', { name })}
      >
        <Heart size={19} strokeWidth={1.6} />
      </button>
      <span className="product-card__badge"><Leaf size={13} aria-hidden="true" />{product.categories.map((c) => tc(categoryLabel(c))).join(' · ')}</span>
      <Link to={url} className="product-card__media" tabIndex={-1} aria-hidden="true">
        <ProductImage image={scene ? product.image : product.cardImage} />
        {scene && product.hoverImage && (
          <ProductImage image={product.hoverImage} className="product-card__hover" />
        )}
      </Link>
      <div className="product-card__body">
        <h3 className="product-card__name">
          <Link to={url}>{product.displayName}</Link>
        </h3>
        <p className="product-card__line" dir={autoDir}>{product.cardLine}</p>
        <p className="product-card__price">
          {formatPrice(product.price)}
          {compare && <s className="product-card__compare"><span className="sr-only">{t('common.compareAt')}</span>{formatPrice(compare)}</s>}
          {!canBuy && <span className="product-card__stock">{statusLabel}</span>}
        </p>
        <div className="product-card__actions">
          {!scene && <Link to={url} className="btn btn--soft">{t('card.details')}</Link>}
          <button
            className={`btn btn--primary ${added ? 'is-added' : ''}`}
            onClick={handleAdd}
            disabled={!canBuy}
            aria-label={!canBuy ? t('card.statusNamed', { name, status: statusLabel })
              : choice ? t('card.chooseOptionOf', { name }) : t('card.addNamed', { name })}
          >
            {added ? <Check size={17} aria-hidden="true" /> : <ShoppingCart size={17} aria-hidden="true" />}
            <span>{added ? t('card.added') : !canBuy ? statusLabel : choice ? t('card.chooseOption') : t('common.addToCart')}</span>
          </button>
        </div>
      </div>
    </article>
  );
}

export default memo(ProductCard);
