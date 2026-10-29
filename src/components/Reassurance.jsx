import { HandCoins, BadgeCheck, Truck, Headset } from 'lucide-react';
import Reveal from './Reveal.jsx';
import { STORE_CONFIG } from '../config/store.js';
import { formatPrice } from '../utils/currency.js';

export const REASSURANCE_ITEMS = [
  { icon: HandCoins, title: 'Paiement à la livraison', text: 'Vous payez à la réception' },
  { icon: BadgeCheck, title: 'Produits authentiques', text: 'Marques coréennes sélectionnées' },
  { icon: Truck, title: 'Livraison partout au Maroc', text: `À domicile · ${formatPrice(STORE_CONFIG.deliveryFee)}` },
  { icon: Headset, title: 'Service client', text: 'Chaque commande confirmée par téléphone' },
];

export default function Reassurance() {
  return (
    <section className="reassurance" aria-label="Nos engagements">
      <ul className="container reassurance__list">
        {REASSURANCE_ITEMS.map(({ icon: Icon, title, text }, i) => (
          <Reveal as="li" key={title} className="reassurance__item" delay={i * 80}>
            <span className="reassurance__icon"><Icon size={22} strokeWidth={1.5} aria-hidden="true" /></span>
            <span>
              <strong>{title}</strong>
              <small>{text}</small>
            </span>
          </Reveal>
        ))}
      </ul>
    </section>
  );
}
