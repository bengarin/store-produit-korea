import { useCallback, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Trash2, ArrowRight, ShoppingBag, X } from 'lucide-react';
import PageHeader from '../components/PageHeader.jsx';
import CartItem from '../components/CartItem.jsx';
import OrderSummary from '../components/OrderSummary.jsx';
import { useCart } from '../context/CartContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { computeTotals, resolveLines } from '../utils/pricing.js';
import { clearDirectOrder } from '../services/orderService.js';

export default function CartPage() {
  const { items, count, setQty, removeItem, clearCart, promo, promoCode, applyPromo, removePromo, maxQty } = useCart();
  const { getProductById, config } = useCatalog();
  const showToast = useToast();
  const navigate = useNavigate();
  const [code, setCode] = useState('');
  const [promoError, setPromoError] = useState('');

  const lines = useMemo(() => resolveLines(items, getProductById), [items, getProductById]);
  const totals = useMemo(() => computeTotals(lines, promo, config), [lines, promo, config]);

  const handleRemove = useCallback(
    (product) => {
      removeItem(product.id);
      showToast(`${product.displayName} retiré du panier`, 'info');
    },
    [removeItem, showToast],
  );

  const handleClear = () => {
    if (window.confirm('Vider entièrement votre panier ?')) {
      clearCart();
      showToast('Panier vidé', 'info');
    }
  };

  const handlePromo = async (e) => {
    e.preventDefault();
    if (!code.trim()) return setPromoError('Saisissez un code promo.');
    const result = await applyPromo(code);
    if (result.ok) {
      setPromoError('');
      setCode('');
      showToast('Code promo appliqué');
    } else {
      setPromoError(result.message);
    }
  };

  const goCheckout = () => {
    clearDirectOrder();
    navigate('/commande');
  };

  const clearBtn = count > 0 && (
    <button className="icon-btn" onClick={handleClear} aria-label="Vider le panier">
      <Trash2 size={22} strokeWidth={1.6} />
    </button>
  );

  return (
    <>
      <PageHeader title={<>Mon panier <span className="muted">({count})</span></>} fallback="/produits" right={clearBtn} />
      <main className="container cart-page">
        {lines.length === 0 ? (
          <div className="empty-state">
            <span className="empty-state__icon"><ShoppingBag size={34} strokeWidth={1.3} /></span>
            <h2>Votre panier est vide</h2>
            <p>Découvrez nos soins coréens et naturels pour commencer votre routine.</p>
            <Link className="btn btn--primary" to="/produits">Découvrir nos produits</Link>
          </div>
        ) : (
          <div className="cart-layout">
            <ul className="cart-list">
              {lines.map(({ product, qty }) => (
                <CartItem key={product.id} product={product} qty={qty} maxQty={maxQty} onQtyChange={setQty} onRemove={handleRemove} />
              ))}
            </ul>

            <aside className="cart-aside">
              {promoCode ? (
                <div className="promo-applied">
                  <span>Code <strong>{promoCode}</strong> appliqué</span>
                  <button className="icon-btn icon-btn--sm" onClick={removePromo} aria-label="Retirer le code promo"><X size={18} /></button>
                </div>
              ) : (
                <form className="promo" onSubmit={handlePromo} noValidate>
                  <label htmlFor="promo" className="sr-only">Code promo</label>
                  <input id="promo" placeholder="Code promo" value={code} autoComplete="off"
                    onChange={(e) => { setCode(e.target.value); setPromoError(''); }}
                    aria-invalid={Boolean(promoError)} aria-describedby={promoError ? 'promo-error' : undefined} />
                  <button className="btn btn--primary" type="submit">Appliquer</button>
                  {promoError && <p className="field__error" id="promo-error" role="alert">{promoError}</p>}
                </form>
              )}

              <OrderSummary totals={totals} promoCode={promoCode} />

              <div className="sticky-actions">
                <button className="btn btn--primary btn--lg btn--block" onClick={goCheckout}>
                  Passer la commande <ArrowRight size={18} />
                </button>
                <Link to="/produits" className="text-link">Continuer mes achats</Link>
              </div>
            </aside>
          </div>
        )}
      </main>
    </>
  );
}
