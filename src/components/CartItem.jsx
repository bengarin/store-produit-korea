import { memo } from 'react';
import { Link } from 'react-router-dom';
import { Trash2 } from 'lucide-react';
import ProductImage from './ProductImage.jsx';
import QuantitySelector from './QuantitySelector.jsx';
import { formatPrice } from '../utils/currency.js';

function CartItem({ product, qty, maxQty, onQtyChange, onRemove }) {
  return (
    <li className="cart-item">
      <Link to={`/produits/${product.id}`} className="cart-item__thumb">
        <ProductImage image={product.images[0]} />
      </Link>
      <div className="cart-item__info">
        <h2 className="cart-item__name">
          <Link to={`/produits/${product.id}`}>{product.displayName}</Link>
        </h2>
        <div className="cart-item__row">
          <span className="cart-item__price">{formatPrice(product.price)}</span>
          <QuantitySelector
            size="sm"
            value={qty}
            max={maxQty}
            onChange={(q) => onQtyChange(product.id, q)}
            label={`Quantité de ${product.displayName}`}
          />
          <button className="icon-btn icon-btn--sm" onClick={() => onRemove(product)} aria-label={`Retirer ${product.displayName} du panier`}>
            <Trash2 size={20} strokeWidth={1.6} />
          </button>
        </div>
      </div>
    </li>
  );
}

export default memo(CartItem);
