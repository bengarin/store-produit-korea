import { useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ShoppingBag } from 'lucide-react';
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

export default function CheckoutPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { items: cartItems, promoCode, clearCart } = useCart();
  const { getProductById } = useCatalog();
  const showToast = useToast();
  const [direct] = useState(() => (params.get('mode') === 'direct' ? loadDirectOrder() : null));
  const [includeCart, setIncludeCart] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const lockRef = useRef(false); // empêche le double envoi

  const isDirect = Boolean(direct);
  const orderItems = useMemo(() => {
    if (!isDirect) return cartItems;
    return includeCart ? mergeItems([direct], cartItems) : [direct];
  }, [isDirect, direct, includeCart, cartItems]);

  const usesCart = !isDirect || includeCart;
  const appliedPromo = usesCart ? promoCode : '';
  const lines = useMemo(() => resolveLines(orderItems, getProductById), [orderItems, getProductById]);
  const totals = useMemo(() => computeTotals(lines, appliedPromo), [lines, appliedPromo]);

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

  const handleSubmit = async (customer) => {
    if (lockRef.current) return;
    lockRef.current = true;
    setSubmitting(true);

    let order;
    try {
      order = await submitOrder({ customer, lines, promoCode: appliedPromo, totals });
    } catch {
      // Échec d'envoi (mode API) : on garde le formulaire rempli et on permet de réessayer.
      lockRef.current = false;
      setSubmitting(false);
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
        <CheckoutForm deliveryFee={totals.delivery} submitting={submitting} onSubmit={handleSubmit}>
          <section className="checkout-section recap">
            <h2>Récapitulatif {isDirect && <span className="pill">Achat direct</span>}</h2>
            <ul className="recap__list">
              {lines.map(({ product, qty, lineTotal }) => (
                <li key={product.id}>
                  <ProductImage image={product.cardImage} className="recap__thumb" />
                  <span className="recap__name">{product.displayName}<small>{qty} × {formatPrice(product.price)}</small></span>
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
            <OrderSummary totals={totals} promoCode={appliedPromo} />
          </section>
        </CheckoutForm>
      </main>
    </>
  );
}
