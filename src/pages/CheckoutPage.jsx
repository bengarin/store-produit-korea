import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { ShoppingBag, AlertTriangle } from 'lucide-react';
import PageHeader from '../components/PageHeader.jsx';
import CheckoutForm from '../components/CheckoutForm.jsx';
import OrderSummary from '../components/OrderSummary.jsx';
import ProductImage from '../components/ProductImage.jsx';
import { useCart } from '../context/CartContext.jsx';
import { formatPrice } from '../utils/currency.js';
import { useToast } from '../context/ToastContext.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { computeTotals, resolveLines, mergeItems } from '../utils/pricing.js';
import { submitOrder, loadDirectOrder, clearDirectOrder, saveLastOrder, ORDERS_ARE_SIMULATED } from '../services/orderService.js';
import { cartParams, track, trackPurchase } from '../analytics/metaPixel.js';
import { createIdempotencyKey } from '../utils/id.js';
import { useI18n } from '../i18n/I18nContext.jsx';

// Début de commande déjà compté pour cette navigation (mode strict : effets appelés deux fois).
let lastCheckoutKey = null;

/** Message clair pour chaque article en rupture renvoyé par le serveur (409 insufficient_stock). */
function stockMessage(t, { name, requested, available, reason }) {
  if (reason === 'insufficient') return t('checkout.stockInsufficient', { name, available, requested });
  return t('checkout.stockUnavailable', { name });
}

export default function CheckoutPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { items: cartItems, promo, clearCart } = useCart();
  const { getProductById, config } = useCatalog();
  const showToast = useToast();
  const { t, lang } = useI18n();
  const { key: locationKey } = useLocation();
  const paymentInfoKeyRef = useRef(null); // AddPaymentInfo : une fois par tentative de commande
  const [direct] = useState(() => (params.get('mode') === 'direct' ? loadDirectOrder() : null));
  const [includeCart, setIncludeCart] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const lockRef = useRef(false); // empêche le double envoi
  // Même clé pour les nouveaux essais d'une MÊME commande (réseau coupé) : le serveur ne la crée qu'une fois.
  const keyRef = useRef(null);
  const [problem, setProblem] = useState(null);

  const isDirect = Boolean(direct);
  const orderItems = useMemo(() => {
    if (!isDirect) return cartItems;
    return includeCart ? mergeItems([direct], cartItems) : [direct];
  }, [isDirect, direct, includeCart, cartItems]);

  const usesCart = !isDirect || includeCart;
  const appliedPromo = usesCart ? promo : null;
  const lines = useMemo(() => resolveLines(orderItems, getProductById), [orderItems, getProductById]);
  const totals = useMemo(() => computeTotals(lines, appliedPromo, config), [lines, appliedPromo, config]);
  // Articles connus comme épuisés / indisponibles : la commande est bloquée (le serveur revérifie de toute façon).
  const unavailable = lines.filter((l) => l.status !== 'available');
  // InitiateCheckout : une fois à l'ouverture de la page de commande (avec des articles).
  const hasLines = lines.length > 0;
  useEffect(() => {
    if (!hasLines || lastCheckoutKey === locationKey) return;
    lastCheckoutKey = locationKey;
    track('InitiateCheckout', cartParams(lines, totals.total));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- uniquement à l'arrivée sur la page
  }, [hasLines, locationKey]);

  const shownProblem = problem || (unavailable.length > 0 && {
    title: t('checkout.unavailableTitle'),
    lines: unavailable.map((l) => t('checkout.unavailableLine', {
      name: `${l.product.displayName}${l.label ? ` (${l.label})` : ''}`, status: t(`status.${l.status}`),
    })),
  });

  if (lines.length === 0) {
    return (
      <>
        <PageHeader title={t('checkout.title')} fallback="/panier" />
        <main className="container empty-state">
          <span className="empty-state__icon"><ShoppingBag size={34} strokeWidth={1.3} /></span>
          <h2>{t('checkout.emptyTitle')}</h2>
          <p>{t('checkout.emptyText')}</p>
          <Link className="btn btn--primary" to="/produits">{t('common.discover')}</Link>
        </main>
      </>
    );
  }

  const handleSubmit = async (customer, { website } = {}) => {
    if (lockRef.current) return;
    if (unavailable.length) return; // message déjà affiché au-dessus du formulaire
    lockRef.current = true;
    setSubmitting(true);
    setProblem(null);
    keyRef.current = keyRef.current || createIdempotencyKey();
    // AddPaymentInfo : formulaire valide envoyé avec le mode de paiement (à la livraison). Une fois par tentative.
    if (paymentInfoKeyRef.current !== keyRef.current) {
      paymentInfoKeyRef.current = keyRef.current;
      track('AddPaymentInfo', { ...cartParams(lines, totals.total), payment_method: 'cod' });
    }

    let order;
    try {
      order = await submitOrder({
        customer, lines, promoCode: appliedPromo?.code || '', totals, idempotencyKey: keyRef.current, website,
      });
    } catch (err) {
      // Échec (mode API) : le formulaire reste rempli.
      lockRef.current = false;
      setSubmitting(false);
      const error = err?.data?.error;
      if (err?.status >= 400 && err?.status < 500) {
        keyRef.current = null; // refus définitif : le prochain essai sera une nouvelle commande
        if (error?.code === 'insufficient_stock') {
          setProblem({ title: t('checkout.stockTitle'), lines: (error.items || []).map((item) => stockMessage(t, item)) });
        } else {
          // Détail renvoyé par le serveur (en français) : affiché tel quel en français, résumé traduit en arabe.
          const fieldMessage = error?.fields?.promoCode?.[0] || error?.fields?.items?.[0];
          const detail = lang === 'fr' ? fieldMessage || err.message : fieldMessage ? t('cart.promoInvalid') : t('checkout.network');
          setProblem({ title: t('checkout.impossible'), lines: [detail] });
        }
        return;
      }
      showToast(t('checkout.network'), 'info');
      return;
    }
    // Purchase : seulement après la création RÉELLE de la commande par le serveur (numéro renvoyé),
    // jamais en démo (commande simulée), une seule fois par numéro de commande.
    if (!ORDERS_ARE_SIMULATED) trackPurchase(order, lines);
    saveLastOrder(order);
    if (usesCart) clearCart();
    if (isDirect) clearDirectOrder();
    navigate('/confirmation', { replace: true });
  };

  return (
    <>
      <PageHeader title={t('checkout.title')} fallback="/panier" />
      <main className="container checkout-page">
        <CheckoutForm
          deliveryFee={totals.delivery}
          submitting={submitting}
          onSubmit={handleSubmit}
          alert={shownProblem && (
            <div className="checkout-alert" role="alert">
              <p className="checkout-alert__title"><AlertTriangle size={18} aria-hidden="true" /> {shownProblem.title}</p>
              <ul>{shownProblem.lines.map((line) => <li key={line}>{line}</li>)}</ul>
              {usesCart && <Link to="/panier" className="text-link">{t('checkout.editCart')}</Link>}
            </div>
          )}
        >
          <section className="checkout-section recap">
            <h2>{t('checkout.recap')} {isDirect && <span className="pill">{t('checkout.direct')}</span>}</h2>
            <ul className="recap__list">
              {lines.map(({ key, product, variant, qty, price, label, status, lineTotal }) => (
                <li key={key}>
                  <ProductImage image={variant?.image || product.cardImage} className="recap__thumb" />
                  <span className="recap__name">
                    {product.displayName}
                    {label && <span className="recap__variant">{label}</span>}
                    {status !== 'available' && <span className="recap__stock">{t(`status.${status}`)}</span>}
                    <small>{qty} × {formatPrice(price)}</small>
                  </span>
                  <strong>{formatPrice(lineTotal)}</strong>
                </li>
              ))}
            </ul>
            {isDirect && cartItems.length > 0 && (
              <label className="checkbox">
                <input type="checkbox" checked={includeCart} onChange={(e) => setIncludeCart(e.target.checked)} />
                {t('checkout.includeCart', { count: cartItems.reduce((s, i) => s + i.qty, 0) })}
              </label>
            )}
            <OrderSummary totals={totals} promoCode={appliedPromo?.code || ''} />
          </section>
        </CheckoutForm>
      </main>
    </>
  );
}
