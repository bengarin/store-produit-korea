import { Minus, Plus } from 'lucide-react';

export default function QuantitySelector({ value, onChange, min = 1, max = 20, size = 'md', label = 'Quantité' }) {
  return (
    <div className={`qty qty--${size}`} role="group" aria-label={label}>
      <button type="button" onClick={() => onChange(value - 1)} disabled={value <= min} aria-label="Diminuer la quantité">
        <Minus size={16} />
      </button>
      <span className="qty__value" aria-live="polite">{value}</span>
      <button type="button" onClick={() => onChange(value + 1)} disabled={value >= max} aria-label="Augmenter la quantité">
        <Plus size={16} />
      </button>
    </div>
  );
}
