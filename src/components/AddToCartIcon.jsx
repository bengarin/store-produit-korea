import { useEffect, useRef, useState } from 'react';
import { ShoppingBag, Check } from 'lucide-react';
import useQuickAdd from '../hooks/useQuickAdd.js';
import { useI18n } from '../i18n/I18nContext.jsx';

/** Bouton carré « ajouter au panier » (rituel), avec confirmation visuelle. */
export default function AddToCartIcon({ product }) {
  const quickAdd = useQuickAdd();
  const { t } = useI18n();
  const [added, setAdded] = useState(false);
  const timer = useRef();
  useEffect(() => () => clearTimeout(timer.current), []);

  const onClick = () => {
    if (!quickAdd(product)) return;
    setAdded(true);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setAdded(false), 1400);
  };

  return (
    <button className={`cart-square ${added ? 'is-added' : ''}`} onClick={onClick} aria-label={t('card.addNamed', { name: product.displayName })}>
      {added ? <Check size={18} aria-hidden="true" /> : <ShoppingBag size={18} aria-hidden="true" />}
    </button>
  );
}
