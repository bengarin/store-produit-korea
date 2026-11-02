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
import { useI18n } from '../i18n/I18nContext.jsx';

export default function CartPage() {
  const { items, count, setQty, removeItem, clearCart, promo, promoCode, applyPromo, removePromo, maxQty } = useCart();
  const { getProductById, config } = useCatalog();
  const showToast = useToast();
  const navigate = useNavigate();
  const { t, tx } = useI18n();
  const [code, setCode] = useState('');
  const [promoError, setPromoError] = useState('');

  const lines = useMemo(() => resolveLines(items, getProductById), [items, getProductById]);
  const totals = useMemo(() => computeTotals(lines, promo, config), [lines, promo, config]);

  const blocked = lines.some((l) => l.status !== 'available');

  const handleRemove = useCallback(
    ({ key, product, label }) => {
      removeItem(key);
      showToast(t('toast.removed', { name: `${product.displayName}${label ? ` (${label})` : ''}` }), 'info');
    },
    [removeItem, showToast, t],
  );

  const handleClear = () => {
    if (window.confirm(t('cart.confirmClear'))) {
      clearCart();
      showToast(t('cart.cleared'), 'info');
    }
  };

  const handlePromo = async (e) => {
    e.preventDefault();
    if (!code.trim()) return setPromoError(t('cart.promoEmpty'));
    const result = await applyPromo(code);
    if (result.ok) {
      setPromoError('');
      setCode('');
      showToast(t('cart.promoOk'));
    } else {
      setPromoError(result.message);
    }
  };

  const goCheckout = () => {
    clearDirectOrder();
    navigate('/commande');
  };

  const clearBtn = count > 0 && (
    <button className="icon-btn" onClick={handleClear} aria-label={t('cart.clear')}>
      <Trash2 size={22} strokeWidth={1.6} />
    </button>
  );

  return (
    <>
      <PageHeader title={<>{t('cart.title')} <span className="muted">({count})</span></>} fallback="/produits" right={clearBtn} />
      <main className="container cart-page">
        {lines.length === 0 ? (
          <div className="empty-state">
            <span className="empty-state__icon"><ShoppingBag size={34} strokeWidth={1.3} /></span>
            <h2>{t('cart.empty')}</h2>
            <p>{t('cart.emptyText')}</p>
            <Link className="btn btn--primary" to="/produits">{t('common.discover')}</Link>
          </div>
        ) : (
          <div className="cart-layout">
            <ul className="cart-list">
              {lines.map((line) => (
                <CartItem key={line.key} line={line} maxQty={maxQty} onQtyChange={setQty} onRemove={handleRemove} />
              ))}
            </ul>

            <aside className="cart-aside">
              {promoCode ? (
                <div className="promo-applied">
                  <span>{tx('cart.promoApplied', { code: <strong>{promoCode}</strong> })}</span>
                  <button className="icon-btn icon-btn--sm" onClick={removePromo} aria-label={t('cart.promoRemove')}><X size={18} /></button>
                </div>
              ) : (
                <form className="promo" onSubmit={handlePromo} noValidate>
                  <label htmlFor="promo" className="sr-only">{t('cart.promo')}</label>
                  <input id="promo" placeholder={t('cart.promo')} value={code} autoComplete="off"
                    onChange={(e) => { setCode(e.target.value); setPromoError(''); }}
                    aria-invalid={Boolean(promoError)} aria-describedby={promoError ? 'promo-error' : undefined} />
                  <button className="btn btn--primary" type="submit">{t('cart.promoApply')}</button>
                  {promoError && <p className="field__error" id="promo-error" role="alert">{promoError}</p>}
                </form>
              )}

              <OrderSummary totals={totals} promoCode={promoCode} />

              <div className="sticky-actions">
                {blocked && <p className="cart-blocked" role="alert">{t('cart.blocked')}</p>}
                <button className="btn btn--primary btn--lg btn--block" onClick={goCheckout} disabled={blocked}>
                  {t('cart.checkout')} <ArrowRight size={18} />
                </button>
                <Link to="/produits" className="text-link">{t('common.continueShopping')}</Link>
              </div>
            </aside>
          </div>
        )}
      </main>
    </>
  );
}
