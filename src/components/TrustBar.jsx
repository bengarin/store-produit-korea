import { Leaf, Truck, ShieldCheck } from 'lucide-react';

const ITEMS = [
  { icon: Leaf, label: 'Produits', sub: 'de qualité' },
  { icon: Truck, label: 'Livraison', sub: 'partout au Maroc' },
  { icon: ShieldCheck, label: 'Paiement', sub: 'à la livraison' },
];

export default function TrustBar() {
  return (
    <ul className="trust container">
      {ITEMS.map(({ icon: Icon, label, sub }) => (
        <li key={label} className="trust__item">
          <span className="trust__icon"><Icon size={26} strokeWidth={1.3} /></span>
          <span>{label}<br />{sub}</span>
        </li>
      ))}
    </ul>
  );
}
