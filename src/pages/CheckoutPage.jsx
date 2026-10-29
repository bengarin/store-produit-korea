import { useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ShoppingBag } from 'lucide-react';
import PageHeader from '../components/PageHeader.jsx';
import CheckoutForm from '../components/CheckoutForm.jsx';
import OrderSummary from '../components/OrderSummary.jsx';
import ProductImage from '../components/ProductImage.jsx';
import { useCart } from '../context/CartContext.jsx';
import { formatPrice } from '../utils/currency.js';
import {
  computeTotals, resolveLines, mergeItems, loadDirectOrder, clearDirectOrder,
  generateOrderNumber, saveLastOrder,
} from '../utils/order.js';

export default function CheckoutPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { items: cartItems, promoCode, clearCart } = useCart();
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
  const lines = useMemo(() => resolveLines(orderItems), [orderItems]);
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

    // Simulation d'envoi : aucune API réelle n'est appelée.
    await new Promise((r) => setTimeout(r, 900));

    const order = {
      number: generateOrderNumber(),
      createdAt: new Date().toISOString(),
      customer,
      lines: lines.map(({ product, qty }) => ({ id: product.id, name: product.displayName, price: product.price, qty })),
      promoCode: totals.discount > 0 ? appliedPromo : '',
      totals,
      payment: 'cod',
      delivery: 'home',
    };
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
                  <ProductImage image={product.images[0]} product={product} className="recap__thumb" />
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
