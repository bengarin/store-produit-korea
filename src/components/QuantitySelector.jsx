import { Minus, Plus } from 'lucide-react';
import { useI18n } from '../i18n/I18nContext.jsx';

export default function QuantitySelector({ value, onChange, min = 1, max = 20, size = 'md', label }) {
  const { t } = useI18n();
  return (
    <div className={`qty qty--${size}`} role="group" aria-label={label || t('qty.label')}>
      <button type="button" onClick={() => onChange(value - 1)} disabled={value <= min} aria-label={t('qty.decrease')}>
        <Minus size={16} />
      </button>
      <span className="qty__value" aria-live="polite">{value}</span>
      <button type="button" onClick={() => onChange(value + 1)} disabled={value >= max} aria-label={t('qty.increase')}>
        <Plus size={16} />
      </button>
    </div>
  );
}
