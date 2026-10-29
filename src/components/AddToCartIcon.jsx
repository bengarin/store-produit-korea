import { useEffect, useRef, useState } from 'react';
import { ShoppingBag, Check } from 'lucide-react';
import { useCart } from '../context/CartContext.jsx';
import { useToast } from '../context/ToastContext.jsx';

/** Bouton carré « ajouter au panier » (rituel), avec confirmation visuelle. */
export default function AddToCartIcon({ product }) {
  const { addItem } = useCart();
  const showToast = useToast();
  const [added, setAdded] = useState(false);
  const t = useRef();
  useEffect(() => () => clearTimeout(t.current), []);

  const onClick = () => {
    addItem(product.id, 1);
    showToast(`${product.displayName} ajouté au panier`);
    setAdded(true);
    clearTimeout(t.current);
    t.current = setTimeout(() => setAdded(false), 1400);
  };

  return (
    <button className={`cart-square ${added ? 'is-added' : ''}`} onClick={onClick} aria-label={`Ajouter ${product.displayName} au panier`}>
      {added ? <Check size={18} aria-hidden="true" /> : <ShoppingBag size={18} aria-hidden="true" />}
    </button>
  );
}
