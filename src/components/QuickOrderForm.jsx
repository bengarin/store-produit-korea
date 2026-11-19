import { useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Check, MessageCircle } from 'lucide-react';
import CheckoutForm from './CheckoutForm.jsx';
import OrderSummary from './OrderSummary.jsx';
import ProductImage from './ProductImage.jsx';
import QuantitySelector from './QuantitySelector.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';
import { ORDERS_ARE_SIMULATED, buildWhatsAppLink, saveLastOrder, submitOrder } from '../services/orderService.js';
import { trackPurchase } from '../analytics/metaPixel.js';
import { computeTotals, resolveLines } from '../utils/pricing.js';
import { formatPrice } from '../utils/currency.js';
import { createIdempotencyKey } from '../utils/id.js';

/** Message clair pour un article en rupture renvoyé par le serveur (409 insufficient_stock), comme au panier. */
function stockMessage(t, { name, requested, available, reason }) {
  if (reason === 'insufficient') return t('checkout.stockInsufficient', { name, available, requested });
  return t('checkout.stockUnavailable', { name });
}

/**
 * Commande rapide : formulaire INTÉGRÉ et déjà ouvert dans la fiche produit (ni bouton, ni fenêtre, ni autre page),
 * sous les informations du produit. Produit et variante choisis, quantité, nom, téléphone, ville, adresse, livraison,
 * frais et total. Même formulaire, mêmes contrôles et même commande que la page de commande
 * (POST /orders, source « quick ») : le serveur revérifie le produit, le réglage, le stock et recalcule tout.
 * Le panier n'est pas touché ; la confirmation s'affiche à la place du formulaire.
 */
export default function QuickOrderForm({ product, variant, initialQty = 1, maxQty }) {
  const { getProductById, config } = useCatalog();
  const { t, lang, tc } = useI18n();
  const showToast = useToast();
  const [qty, setQty] = useState(Math.max(1, Math.min(maxQty, initialQty)));
  const [submitting, setSubmitting] = useState(false);
  const [problem, setProblem] = useState(null);
  const [order, setOrder] = useState(null);
  const lockRef = useRef(false);
  const keyRef = useRef(null); // même clé pour un nouvel essai de la MÊME commande (réseau coupé)
  const sectionRef = useRef(null);

  const items = useMemo(() => [variant ? { id: product.id, variantId: variant.id, qty } : { id: product.id, qty }], [product.id, variant, qty]);
  const lines = useMemo(() => resolveLines(items, getProductById), [items, getProductById]);
  const totals = useMemo(() => computeTotals(lines, null, config), [lines, config]);
  const line = lines[0];

  // Après la confirmation seulement : la section défile jusqu'à l'écran (le formulaire, lui, est déjà ouvert).
  useEffect(() => {
    const el = sectionRef.current;
    if (!order || !el) return;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    el.focus({ preventScroll: true });
  }, [order]);

  // Autre variante choisie sur la fiche = autre commande.
  useEffect(() => {
    keyRef.current = null;
    setProblem(null);
  }, [variant]);

  const changeQty = (value) => {
    setQty(Math.max(1, Math.min(maxQty, value)));
    keyRef.current = null; // autre contenu = autre commande
    setProblem(null);
  };

  const handleSubmit = async (customer, { website } = {}) => {
    if (lockRef.current || !line) return;
    if (line.status !== 'available') {
      setProblem({ title: t('checkout.unavailableTitle'), lines: [t('checkout.stockUnavailable', { name: product.displayName })] });
      return;
    }
    lockRef.current = true;
    setSubmitting(true);
    setProblem(null);
    keyRef.current = keyRef.current || createIdempotencyKey();
    let created;
    try {
      created = await submitOrder({
        customer, lines, promoCode: '', totals, idempotencyKey: keyRef.current, website, source: 'quick',
      });
    } catch (err) {
      lockRef.current = false;
      setSubmitting(false);
      const error = err?.data?.error;
      if (err?.status >= 400 && err?.status < 500) {
        keyRef.current = null; // refus définitif : le prochain essai sera une nouvelle commande
        if (error?.code === 'insufficient_stock') {
          setProblem({ title: t('checkout.stockTitle'), lines: (error.items || []).map((item) => stockMessage(t, item)) });
        } else {
          const fieldMessage = error?.fields?.items?.[0];
          const detail = lang === 'fr' ? fieldMessage || err.message : t('quick.unavailable');
          setProblem({ title: t('checkout.impossible'), lines: [detail] });
        }
        return;
      }
      showToast(t('checkout.network'), 'info');
      return;
    }
    if (!ORDERS_ARE_SIMULATED) trackPurchase(created, lines);
    saveLastOrder(created);
    setSubmitting(false);
    setOrder(created); // confirmation affichée ici même ; lockRef reste fermé (pas de double commande)
  };

  if (order) {
    const waLink = buildWhatsAppLink(order.number, config);
    return (
      <section className="quick-order quick-order--done" ref={sectionRef} tabIndex={-1} aria-labelledby="quick-order-done" role="status">
        <div className="quick-order__success">
          <span className="quick-order__check" aria-hidden="true"><Check size={26} strokeWidth={2.4} /></span>
          <h2 id="quick-order-done">{t('confirm.title')}</h2>
          <p>{t('confirm.text')}</p>
        </div>
        <dl className="quick-order__recap">
          <div><dt>{t('confirm.number')}</dt><dd><strong>#{order.number}</strong></dd></div>
          <div><dt>{t('confirm.products')}</dt><dd>{t('confirm.items', { count: order.totals.itemCount })}</dd></div>
          <div><dt>{t('summary.total')}</dt><dd><strong>{formatPrice(order.totals.total)}</strong></dd></div>
          <div><dt>{t('confirm.payment')}</dt><dd>{t('confirm.paymentValue')}</dd></div>
          <div><dt>{t('confirm.shipTo')}</dt><dd>{order.customer.fullName}, {tc(order.customer.city)}</dd></div>
        </dl>
        {waLink && (
          <a className="btn btn--outline btn--block" href={waLink} target="_blank" rel="noopener noreferrer">
            <MessageCircle size={18} aria-hidden="true" /> {t('confirm.whatsapp')}
          </a>
        )}
        {ORDERS_ARE_SIMULATED && <p className="demo-note">{t('confirm.demo')}</p>}
      </section>
    );
  }

  return (
    <section className="quick-order" ref={sectionRef} tabIndex={-1} aria-labelledby="quick-order-title">
      <header className="quick-order__head">
        <h2 id="quick-order-title">{t('quick.title')}</h2>
      </header>

      <div className="quick-order__product">
        <ProductImage image={variant?.image || product.cardImage} className="quick-order__thumb" />
        <div className="quick-order__info">
          <p className="quick-order__name">{product.displayName}</p>
          {line?.label && <p className="quick-order__variant">{line.label}</p>}
          <p className="quick-order__price">{formatPrice(line?.price ?? product.price)}</p>
        </div>
        <div className="quick-order__qty">
          <span className="quick-order__qty-label" aria-hidden="true">{t('quick.qty')}</span>
          <QuantitySelector value={qty} onChange={changeQty} max={maxQty} label={t('quick.qty')} />
        </div>
      </div>

      <CheckoutForm
        deliveryFee={totals.delivery}
        submitting={submitting}
        onSubmit={handleSubmit}
        submitLabel={t('quick.submit', { total: formatPrice(totals.total) })}
        alert={problem && (
          <div className="checkout-alert" role="alert">
            <p className="checkout-alert__title"><AlertTriangle size={18} aria-hidden="true" /> {problem.title}</p>
            <ul>{problem.lines.map((text) => <li key={text}>{text}</li>)}</ul>
          </div>
        )}
      >
        <section className="checkout-section quick-order__summary">
          <OrderSummary totals={totals} promoCode="" />
        </section>
      </CheckoutForm>
    </section>
  );
}
