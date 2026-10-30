import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, Heart, MessageCircle, Info } from 'lucide-react';
import { loadLastOrder, buildWhatsAppLink, ORDERS_ARE_SIMULATED } from '../services/orderService.js';
import { formatPrice } from '../utils/currency.js';
import { useCatalog } from '../context/CatalogContext.jsx';

export default function ConfirmationPage() {
  const [order] = useState(loadLastOrder);
  const [showWaHelp, setShowWaHelp] = useState(false);
  const { config } = useCatalog();

  if (!order) {
    return (
      <main className="confirmation">
        <div className="confirmation__inner container empty-state">
          <h1>Aucune commande récente</h1>
          <p>Nous n’avons pas trouvé de commande sur cet appareil.</p>
          <Link className="btn btn--primary" to="/produits">Découvrir nos produits</Link>
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
        <h1 className="confirmation__title">Commande confirmée !</h1>
        <p className="confirmation__thanks">Merci pour votre confiance <Heart size={18} className="heart" fill="currentColor" /></p>
        <p className="confirmation__text">
          Nous avons bien reçu votre commande. Vous serez contacté(e) prochainement pour confirmer les détails.
        </p>

        <section className="order-card" aria-labelledby="order-details">
          <h2 id="order-details">Détails de la commande</h2>
          <div className="order-card__number">
            <span>Numéro de commande</span>
            <strong>#{order.number}</strong>
          </div>
          <dl>
            <div><dt>Produits</dt><dd>{totals.itemCount} article{totals.itemCount > 1 ? 's' : ''}</dd></div>
            <div><dt>Sous-total</dt><dd>{formatPrice(totals.subtotal)}</dd></div>
            {totals.discount > 0 && (
              <div><dt>Remise ({order.promoCode})</dt><dd>−{formatPrice(totals.discount)}</dd></div>
            )}
            <div><dt>Livraison</dt><dd>À domicile ({totals.delivery === 0 ? 'offerte' : formatPrice(totals.delivery)})</dd></div>
            <div className="order-card__total"><dt>Total</dt><dd>{formatPrice(totals.total)}</dd></div>
            <div><dt>Mode de paiement</dt><dd>À la livraison (COD)</dd></div>
            <div><dt>Livraison à</dt><dd>{order.customer.fullName}, {order.customer.city}</dd></div>
          </dl>
        </section>

        <div className="confirmation__actions">
          <Link to="/produits" className="btn btn--primary btn--lg btn--block">Continuer mes achats</Link>
          {waLink ? (
            <a className="btn btn--outline btn--lg btn--block" href={waLink} target="_blank" rel="noopener noreferrer">
              <MessageCircle size={19} /> Suivre ma commande sur WhatsApp
            </a>
          ) : (
            <button className="btn btn--outline btn--lg btn--block" onClick={() => setShowWaHelp((v) => !v)} aria-expanded={showWaHelp}>
              <MessageCircle size={19} /> Suivre ma commande sur WhatsApp
            </button>
          )}
          {showWaHelp && (
            <p className="config-hint" role="note">
              <Info size={15} />
              {ORDERS_ARE_SIMULATED ? (
                <span>Numéro WhatsApp non configuré. Renseignez <code>whatsappNumber</code> dans <code>src/config/store.js</code>.</span>
              ) : (
                <span>Le suivi WhatsApp n’est pas encore disponible : nous vous contacterons par téléphone pour confirmer votre commande.</span>
              )}
            </p>
          )}
        </div>

        {ORDERS_ARE_SIMULATED && <p className="demo-note">Démo front-end : cette commande est simulée et n’a été transmise à aucun service.</p>}
      </div>
    </main>
  );
}
