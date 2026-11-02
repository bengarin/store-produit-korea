import { formatPrice } from '../utils/currency.js';
import { useI18n } from '../i18n/I18nContext.jsx';

/** Bloc Sous-total / Remise / Livraison / Total. */
export default function OrderSummary({ totals, promoCode }) {
  const { t } = useI18n();
  return (
    <dl className="summary">
      <div className="summary__row">
        <dt>{t('summary.subtotal')}</dt>
        <dd>{formatPrice(totals.subtotal)}</dd>
      </div>
      {totals.discount > 0 && (
        <div className="summary__row summary__row--discount">
          <dt>{t('summary.discount', { code: promoCode })}</dt>
          <dd>−{formatPrice(totals.discount)}</dd>
        </div>
      )}
      <div className="summary__row">
        <dt>{t('summary.delivery')}</dt>
        <dd>{totals.delivery === 0 && totals.itemCount > 0 ? t('summary.free') : formatPrice(totals.delivery)}</dd>
      </div>
      <div className="summary__row summary__row--total">
        <dt>{t('summary.total')}</dt>
        <dd>{formatPrice(totals.total)}</dd>
      </div>
    </dl>
  );
}
