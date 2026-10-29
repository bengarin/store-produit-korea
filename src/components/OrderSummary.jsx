import { formatPrice } from '../utils/currency.js';

/** Bloc Sous-total / Remise / Livraison / Total. */
export default function OrderSummary({ totals, promoCode }) {
  return (
    <dl className="summary">
      <div className="summary__row">
        <dt>Sous-total</dt>
        <dd>{formatPrice(totals.subtotal)}</dd>
      </div>
      {totals.discount > 0 && (
        <div className="summary__row summary__row--discount">
          <dt>Remise ({promoCode})</dt>
          <dd>−{formatPrice(totals.discount)}</dd>
        </div>
      )}
      <div className="summary__row">
        <dt>Frais de livraison</dt>
        <dd>{totals.delivery === 0 && totals.itemCount > 0 ? 'Offerts' : formatPrice(totals.delivery)}</dd>
      </div>
      <div className="summary__row summary__row--total">
        <dt>Total</dt>
        <dd>{formatPrice(totals.total)}</dd>
      </div>
    </dl>
  );
}
