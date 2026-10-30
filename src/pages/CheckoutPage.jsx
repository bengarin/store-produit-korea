import { useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
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
import { submitOrder, loadDirectOrder, clearDirectOrder, saveLastOrder } from '../services/orderService.js';
import { createIdempotencyKey } from '../utils/id.js';
import { STATUS_LABELS } from '../utils/variants.js';

/** Message clair pour chaque article en rupture renvoyé par le serveur (409 insufficient_stock). */
function stockMessage({ name, requested, available, reason }) {
  if (reason === 'insufficient') {
    return `${name} : il n’en reste que ${available} (vous en demandez ${requested}).`;
  }
  return `${name} : momentanément indisponible.`;
}

export default function CheckoutPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { items: cartItems, promo, clearCart } = useCart();
  const { getProductById, config } = useCatalog();
  const showToast = useToast();
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
  const shownProblem = problem || (unavailable.length > 0 && {
    title: 'Article indisponible',
    lines: unavailable.map((l) => `${l.product.displayName}${l.label ? ` (${l.label})` : ''} : ${STATUS_LABELS[l.status].toLowerCase()}.`),
  });

  if (lines.length === 0) {
    return (
      <>
        <PageHeader title="Finaliser ma commande" fallback="/panier" />
        <main className="container empty-state">
          <span className="empty-state__icon"><ShoppingBag size={34} strokeWidth={1.3} /></span>
          <h2>Aucun article à commander</h2>
          <p>Ajoutez des produits à votre panier pour passer commande.</p>
          <Link className="btn btn--primary" to="/produits">Découvrir nos produits</Link>
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
          setProblem({ title: 'Stock insuffisant', lines: (error.items || []).map(stockMessage) });
        } else {
          const fieldMessage = error?.fields?.promoCode?.[0] || error?.fields?.items?.[0];
          setProblem({ title: 'Commande impossible', lines: [fieldMessage || err.message] });
        }
        return;
      }
      showToast('La commande n’a pas pu être envoyée. Vérifiez votre connexion et réessayez.', 'info');
      return;
    }
    saveLastOrder(order);
    if (usesCart) clearCart();
    if (isDirect) clearDirectOrder();
    navigate('/confirmation', { replace: true });
  };

  return (
    <>
      <PageHeader title="Finaliser ma commande" fallback="/panier" />
      <main className="container checkout-page">
        <CheckoutForm
          deliveryFee={totals.delivery}
          submitting={submitting}
          onSubmit={handleSubmit}
          alert={shownProblem && (
            <div className="checkout-alert" role="alert">
              <p className="checkout-alert__title"><AlertTriangle size={18} aria-hidden="true" /> {shownProblem.title}</p>
              <ul>{shownProblem.lines.map((line) => <li key={line}>{line}</li>)}</ul>
              {usesCart && <Link to="/panier" className="text-link">Modifier mon panier</Link>}
            </div>
          )}
        >
          <section className="checkout-section recap">
            <h2>Récapitulatif {isDirect && <span className="pill">Achat direct</span>}</h2>
            <ul className="recap__list">
              {lines.map(({ key, product, variant, qty, price, label, status, lineTotal }) => (
                <li key={key}>
                  <ProductImage image={variant?.image || product.cardImage} className="recap__thumb" />
                  <span className="recap__name">
                    {product.displayName}
                    {label && <span className="recap__variant">{label}</span>}
                    {status !== 'available' && <span className="recap__stock">{STATUS_LABELS[status]}</span>}
                    <small>{qty} × {formatPrice(price)}</small>
                  </span>
                  <strong>{formatPrice(lineTotal)}</strong>
                </li>
              ))}
            </ul>
            {isDirect && cartItems.length > 0 && (
              <label className="checkbox">
                <input type="checkbox" checked={includeCart} onChange={(e) => setIncludeCart(e.target.checked)} />
                Ajouter aussi les {cartItems.reduce((s, i) => s + i.qty, 0)} article(s) de mon panier à cette commande
              </label>
            )}
            <OrderSummary totals={totals} promoCode={appliedPromo?.code || ''} />
          </section>
        </CheckoutForm>
      </main>
    </>
  );
}
