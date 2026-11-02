import { HandCoins, BadgeCheck, Truck, Headset, Leaf, Sparkles, Gift, ShieldCheck, Phone, Heart, Package, Clock } from 'lucide-react';
import Reveal from './Reveal.jsx';
import { STORE_CONFIG } from '../config/store.js';
import { useCatalog } from '../context/CatalogContext.jsx';
import { formatPrice } from '../utils/currency.js';

/** Icônes autorisées dans le thème (liste fermée, voir shared/theme/schema.json « icons »). */
export const BENEFIT_ICONS = {
  'hand-coins': HandCoins, 'badge-check': BadgeCheck, truck: Truck, headset: Headset, leaf: Leaf, sparkles: Sparkles,
  gift: Gift, 'shield-check': ShieldCheck, phone: Phone, heart: Heart, package: Package, clock: Clock,
};

// Engagements de la fiche produit (fixes, hors thème).
export const REASSURANCE_ITEMS = [
  { icon: HandCoins, title: 'Paiement à la livraison', text: 'Vous payez à la réception' },
  { icon: BadgeCheck, title: 'Produits authentiques', text: 'Marques coréennes sélectionnées' },
  { icon: Truck, title: 'Livraison partout au Maroc', text: `À domicile · ${formatPrice(STORE_CONFIG.deliveryFee)}` },
  { icon: Headset, title: 'Service client', text: 'Chaque commande confirmée par téléphone' },
];

/** Avantages de la boutique (section « benefits » du thème). {frais_livraison} = frais de livraison actuels. */
export default function Reassurance({ section }) {
  const { config } = useCatalog();
  const fee = formatPrice(config?.deliveryFee ?? STORE_CONFIG.deliveryFee);
  const items = section.items || [];
  if (!items.length) return null;
  return (
    <section className="reassurance" aria-label="Nos engagements">
      <ul className="container reassurance__list">
        {items.map(({ icon, title, text }, i) => {
          const Icon = BENEFIT_ICONS[icon] || BadgeCheck;
          return (
            <Reveal as="li" key={`${i}-${title}`} className="reassurance__item" delay={i * 80}>
              <span className="reassurance__icon"><Icon size={22} strokeWidth={1.5} aria-hidden="true" /></span>
              <span>
                <strong>{title}</strong>
                {text && <small>{text.replaceAll('{frais_livraison}', fee)}</small>}
              </span>
            </Reveal>
          );
        })}
      </ul>
    </section>
  );
}
