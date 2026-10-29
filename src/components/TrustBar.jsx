import { Leaf, Truck, ShieldCheck } from 'lucide-react';

const ITEMS = [
  { icon: Leaf, label: 'Produits', sub: 'de qualité' },
  { icon: Truck, label: 'Livraison', sub: 'partout au Maroc' },
  { icon: ShieldCheck, label: 'Paiement', sub: 'à la livraison' },
];

export default function TrustBar({ className = '', id }) {
  return (
    <ul className={`trust ${className}`} id={id}>
      {ITEMS.map(({ icon: Icon, label, sub }) => (
        <li key={label} className="trust__item">
          <span className="trust__icon"><Icon size={22} strokeWidth={1.4} /></span>
          <span className="trust__text">{label}<br />{sub}</span>
        </li>
      ))}
    </ul>
  );
}
