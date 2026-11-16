import { useEffect, useId, useState } from 'react';
import { ChevronDown, SlidersHorizontal } from 'lucide-react';
import { useI18n } from '../i18n/I18nContext.jsx';

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/**
 * Filtre « Prix » (en DH) : champs minimum / maximum + curseur à deux poignées, bouton « Appliquer ».
 * `bounds` = prix le plus bas et le plus haut du catalogue ; `value` = filtre appliqué ({ min, max } ou null).
 */
export default function PriceFilter({ bounds, value, onApply, extra = null }) {
  const { t, lang } = useI18n();
  const id = useId();
  // Filtre appliqué, ramené aux bornes affichables (?prix_min seul = « jusqu'au prix le plus haut »).
  const vMin = value ? value.min : bounds.min;
  const vMax = value && Number.isFinite(value.max) ? value.max : bounds.max;
  const [open, setOpen] = useState(Boolean(value));
  const [draft, setDraft] = useState({ min: vMin, max: vMax });
  const [error, setError] = useState('');
  const unit = lang === 'ar' ? 'درهم' : 'DH';

  useEffect(() => {
    setDraft({ min: vMin, max: vMax });
    setError('');
  }, [vMin, vMax]);

  const span = Math.max(1, bounds.max - bounds.min);
  const pct = (v) => ((clamp(Number(v) || 0, bounds.min, bounds.max) - bounds.min) / span) * 100;

  const apply = (e) => {
    e.preventDefault();
    const min = draft.min === '' ? bounds.min : Math.floor(Number(draft.min));
    const max = draft.max === '' ? bounds.max : Math.ceil(Number(draft.max));
    if (Number.isNaN(min) || Number.isNaN(max) || min < 0 || max < 0) return setError(t('price.invalid'));
    if (min > max) return setError(t('price.invalid'));
    setError('');
    // Toute la plage = aucun filtre.
    onApply(min <= bounds.min && max >= bounds.max ? null : { min, max });
  };

  // « 30 – 50 DH » isolé du sens de lecture (sinon l'arabe inverse les nombres et l'unité).
  const label = value ? <bdi>{t('price.range', { min: vMin, max: `${vMax} ${unit}` })}</bdi> : t('price.title');

  return (
    <div className={`price-filter ${open ? 'is-open' : ''}`}>
      <div className="price-filter__bar">
      <button type="button" className={`chip price-filter__toggle ${value ? 'is-active' : ''}`} aria-expanded={open} aria-controls={`${id}-panel`}
        onClick={() => setOpen((o) => !o)}>
        <SlidersHorizontal size={16} aria-hidden="true" />
        <span className="sr-only">{t('price.toggle')} : </span>{label}
        <ChevronDown size={16} aria-hidden="true" className="price-filter__chevron" />
      </button>
      {extra}
      </div>
      {open && (
        <form id={`${id}-panel`} className="price-filter__panel" onSubmit={apply} noValidate>
          <div className="price-filter__fields">
            <label className="price-filter__field">
              <span>{t('price.min')}</span>
              <span className="price-filter__input">
                <input type="number" inputMode="numeric" min={0} step={1} value={draft.min}
                  onChange={(e) => setDraft((d) => ({ ...d, min: e.target.value }))} />
                <span aria-hidden="true">{unit}</span>
              </span>
            </label>
            <span className="price-filter__dash" aria-hidden="true">–</span>
            <label className="price-filter__field">
              <span>{t('price.max')}</span>
              <span className="price-filter__input">
                <input type="number" inputMode="numeric" min={0} step={1} value={draft.max}
                  onChange={(e) => setDraft((d) => ({ ...d, max: e.target.value }))} />
                <span aria-hidden="true">{unit}</span>
              </span>
            </label>
          </div>
          {bounds.max > bounds.min && (
            <div className="price-range" style={{ '--from': `${pct(draft.min)}%`, '--to': `${pct(draft.max)}%` }}>
              <span className="price-range__track" aria-hidden="true" />
              <input type="range" min={bounds.min} max={bounds.max} step={1} aria-label={t('price.min')}
                value={clamp(Number(draft.min) || bounds.min, bounds.min, bounds.max)}
                onChange={(e) => setDraft((d) => ({ ...d, min: Math.min(Number(e.target.value), Number(d.max) || bounds.max) }))} />
              <input type="range" min={bounds.min} max={bounds.max} step={1} aria-label={t('price.max')}
                value={clamp(Number(draft.max) || bounds.max, bounds.min, bounds.max)}
                onChange={(e) => setDraft((d) => ({ ...d, max: Math.max(Number(e.target.value), Number(d.min) || bounds.min) }))} />
            </div>
          )}
          {error && <p className="field__error" role="alert">{error}</p>}
          <button type="submit" className="btn btn--primary price-filter__apply">{t('price.apply')}</button>
        </form>
      )}
    </div>
  );
}
