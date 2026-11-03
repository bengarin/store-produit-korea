import { HandCoins, BadgeCheck, Truck, Headset, Leaf, Sparkles, Gift, ShieldCheck, Phone, Heart, Package, Clock } from 'lucide-react';
import Reveal from './Reveal.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { formatPrice } from '../utils/currency.js';
import { useI18n } from '../i18n/I18nContext.jsx';

/** Icônes autorisées dans le thème (liste fermée, voir shared/theme/schema.json « icons »). */
export const BENEFIT_ICONS = {
  'hand-coins': HandCoins, 'badge-check': BadgeCheck, truck: Truck, headset: Headset, leaf: Leaf, sparkles: Sparkles,
  gift: Gift, 'shield-check': ShieldCheck, phone: Phone, heart: Heart, package: Package, clock: Clock,
};

// Engagements de la fiche produit (fixes, hors thème) : textes dans src/i18n/messages.js (« trust.* »).
/** Frais de livraison affichés : « Offerte » à 0 DH, le montant sinon, rien s'il n'est pas configuré. */
export function deliveryFeeLabel(t, fee) {
  if (fee == null) return null;
  return Number(fee) === 0 ? t('form.free') : formatPrice(fee);
}

/** `fee` : frais de la configuration de la boutique (serveur en mode API) ; null = non affiché. */
export function reassuranceItems(t, fee = null) {
  const label = deliveryFeeLabel(t, fee);
  return [
    { icon: HandCoins, title: t('trust.cod.title'), text: t('trust.cod.text') },
    { icon: BadgeCheck, title: t('trust.authentic.title'), text: t('trust.authentic.text') },
    { icon: Truck, title: t('trust.delivery.title'), text: label ? t('trust.delivery.text', { fee: label }) : t('trust.delivery.textNoFee') },
    { icon: Headset, title: t('trust.service.title'), text: t('trust.service.text') },
  ];
}

/** Avantages de la boutique (section « benefits » du thème). {frais_livraison} = frais de livraison actuels. */
export default function Reassurance({ section }) {
  const { config } = useCatalog();
  const { t, tc } = useI18n();
  const fee = deliveryFeeLabel(t, config?.deliveryFee) ?? '';
  const items = section.items || [];
  if (!items.length) return null;
  return (
    <section className="reassurance" aria-label={t('benefits.label')}>
      <ul className="container reassurance__list">
        {items.map(({ icon, title, text }, i) => {
          const Icon = BENEFIT_ICONS[icon] || BadgeCheck;
          return (
            <Reveal as="li" key={`${i}-${title}`} className="reassurance__item" delay={i * 80}>
              <span className="reassurance__icon"><Icon size={22} strokeWidth={1.5} aria-hidden="true" /></span>
              <span>
                <strong>{tc(title)}</strong>
                {text && <small>{tc(text).replaceAll('{frais_livraison}', fee)}</small>}
              </span>
            </Reveal>
          );
        })}
      </ul>
    </section>
  );
}
