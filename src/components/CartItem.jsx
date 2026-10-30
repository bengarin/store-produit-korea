import { memo } from 'react';
import { Link } from 'react-router-dom';
import { Trash2 } from 'lucide-react';
import ProductImage from './ProductImage.jsx';
import QuantitySelector from './QuantitySelector.jsx';
import { formatPrice } from '../utils/currency.js';
import { STATUS_LABELS } from '../utils/variants.js';

/** `line` = ligne résolue (utils/pricing.js → resolveLines) : produit, variante, prix, libellé, disponibilité. */
function CartItem({ line, maxQty, onQtyChange, onRemove }) {
  const { product, variant, qty, price, label, status, key } = line;
  const name = label ? `${product.displayName} (${label})` : product.displayName;
  return (
    <li className={status === 'available' ? 'cart-item' : 'cart-item is-unavailable'}>
      <Link to={`/produits/${product.id}`} className="cart-item__thumb">
        <ProductImage image={variant?.image || product.cardImage} />
      </Link>
      <div className="cart-item__info">
        <h2 className="cart-item__name">
          <Link to={`/produits/${product.id}`}>{product.displayName}</Link>
        </h2>
        {label && <p className="cart-item__variant">{label}</p>}
        {status !== 'available' && (
          <p className="cart-item__stock" role="status">{STATUS_LABELS[status]} — retirez cet article pour commander.</p>
        )}
        <div className="cart-item__row">
          <span className="cart-item__price">{formatPrice(price)}</span>
          <QuantitySelector
            size="sm"
            value={qty}
            max={maxQty}
            onChange={(q) => onQtyChange(key, q)}
            label={`Quantité de ${name}`}
          />
          <button className="icon-btn icon-btn--sm" onClick={() => onRemove(line)} aria-label={`Retirer ${name} du panier`}>
            <Trash2 size={20} strokeWidth={1.6} />
          </button>
        </div>
      </div>
    </li>
  );
}

export default memo(CartItem);
