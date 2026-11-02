import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, Heart, MessageCircle, Info } from 'lucide-react';
import { loadLastOrder, buildWhatsAppLink, ORDERS_ARE_SIMULATED } from '../services/orderService.js';
import { formatPrice } from '../utils/currency.js';
import { useCatalog } from '../context/CatalogContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

export default function ConfirmationPage() {
  const [order] = useState(loadLastOrder);
  const [showWaHelp, setShowWaHelp] = useState(false);
  const { config } = useCatalog();
  const { t, tx, tc } = useI18n();

  if (!order) {
    return (
      <main className="confirmation">
        <div className="confirmation__inner container empty-state">
          <h1>{t('confirm.noneTitle')}</h1>
          <p>{t('confirm.noneText')}</p>
          <Link className="btn btn--primary" to="/produits">{t('common.discover')}</Link>
        </div>
      </main>
    );
  }

  const { totals } = order;
  const waLink = buildWhatsAppLink(order.number, config);

  return (
    <main className="confirmation">
      <div className="confirmation__inner container">
        <div className="success-mark" aria-hidden="true"><Check size={46} strokeWidth={2.4} /></div>
        <h1 className="confirmation__title">{t('confirm.title')}</h1>
        <p className="confirmation__thanks">{t('confirm.thanks')} <Heart size={18} className="heart" fill="currentColor" /></p>
        <p className="confirmation__text">
          {t('confirm.text')}
        </p>

        <section className="order-card" aria-labelledby="order-details">
          <h2 id="order-details">{t('confirm.details')}</h2>
          <div className="order-card__number">
            <span>{t('confirm.number')}</span>
            <strong>#{order.number}</strong>
          </div>
          <dl>
            <div><dt>{t('confirm.products')}</dt><dd>{t('confirm.items', { count: totals.itemCount })}</dd></div>
            <div><dt>{t('summary.subtotal')}</dt><dd>{formatPrice(totals.subtotal)}</dd></div>
            {totals.discount > 0 && (
              <div><dt>{t('summary.discount', { code: order.promoCode })}</dt><dd>−{formatPrice(totals.discount)}</dd></div>
            )}
            <div><dt>{t('confirm.delivery')}</dt><dd>{t('confirm.deliveryValue', { fee: totals.delivery === 0 ? t('confirm.free') : formatPrice(totals.delivery) })}</dd></div>
            <div className="order-card__total"><dt>{t('summary.total')}</dt><dd>{formatPrice(totals.total)}</dd></div>
            <div><dt>{t('confirm.payment')}</dt><dd>{t('confirm.paymentValue')}</dd></div>
            <div><dt>{t('confirm.shipTo')}</dt><dd>{order.customer.fullName}, {tc(order.customer.city)}</dd></div>
          </dl>
        </section>

        <div className="confirmation__actions">
          <Link to="/produits" className="btn btn--primary btn--lg btn--block">Continuer mes achats</Link>
          {waLink ? (
            <a className="btn btn--outline btn--lg btn--block" href={waLink} target="_blank" rel="noopener noreferrer">
              <MessageCircle size={19} /> {t('confirm.whatsapp')}
            </a>
          ) : (
            <button className="btn btn--outline btn--lg btn--block" onClick={() => setShowWaHelp((v) => !v)} aria-expanded={showWaHelp}>
              <MessageCircle size={19} /> {t('confirm.whatsapp')}
            </button>
          )}
          {showWaHelp && (
            <p className="config-hint" role="note">
              <Info size={15} />
              {ORDERS_ARE_SIMULATED ? (
                <span>{tx('confirm.waDemoHint', { field: <code>whatsappNumber</code>, file: <code>src/config/store.js</code> })}</span>
              ) : (
                <span>{t('confirm.waHint')}</span>
              )}
            </p>
          )}
        </div>

        {ORDERS_ARE_SIMULATED && <p className="demo-note">{t('confirm.demo')}</p>}
      </div>
    </main>
  );
}
