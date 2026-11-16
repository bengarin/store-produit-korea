import { useEffect, useState } from 'react';
import { useI18n } from '../i18n/I18nContext.jsx';

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/** Plage « toute la fourchette » = aucun filtre (null). Sinon { min, max } en DH entiers. */
export function normalizeRange(draft, bounds) {
  const min = draft.min === '' ? bounds.min : Math.floor(Number(draft.min));
  const max = draft.max === '' ? bounds.max : Math.ceil(Number(draft.max));
  if (Number.isNaN(min) || Number.isNaN(max) || min < 0 || max < 0 || min > max) return { error: true };
  return { range: min <= bounds.min && max >= bounds.max ? null : { min, max } };
}

/**
 * Prix minimum / maximum (DH) + curseur à deux poignées, bornes = prix réels du catalogue.
 * - `onApply` fourni : bouton « Appliquer » (barre latérale sur ordinateur).
 * - sinon : chaque changement est remonté par `onDraft` (tiroir mobile, appliqué avec tout le reste).
 */
export default function PriceRange({ bounds, value, onApply, onDraft }) {
  const { t, lang } = useI18n();
  const unit = lang === 'ar' ? 'درهم' : 'DH';
  const vMin = value ? value.min : bounds.min;
  const vMax = value && Number.isFinite(value.max) ? value.max : bounds.max;
  const [draft, setDraft] = useState({ min: vMin, max: vMax });
  const [error, setError] = useState('');

  useEffect(() => {
    setDraft({ min: vMin, max: vMax });
    setError('');
  }, [vMin, vMax]);

  const update = (next) => {
    setDraft(next);
    setError('');
    if (onDraft) {
      const r = normalizeRange(next, bounds);
      if (r.error) setError(t('price.invalid'));
      else onDraft(r.range);
    }
  };
  const apply = (e) => {
    e.preventDefault();
    const r = normalizeRange(draft, bounds);
    if (r.error) return setError(t('price.invalid'));
    onApply(r.range);
  };

  const span = Math.max(1, bounds.max - bounds.min);
  const pct = (v) => ((clamp(Number(v) || 0, bounds.min, bounds.max) - bounds.min) / span) * 100;
  const Tag = onApply ? 'form' : 'div';

  return (
    <Tag className="price-range-box" {...(onApply ? { onSubmit: apply, noValidate: true } : {})}>
      <div className="price-filter__fields">
        <label className="price-filter__field">
          <span>{t('price.minShort')}</span>
          <span className="price-filter__input">
            <input type="number" inputMode="numeric" min={0} step={1} value={draft.min} aria-label={t('price.min')}
              onChange={(e) => update({ ...draft, min: e.target.value })} />
            <span aria-hidden="true">{unit}</span>
          </span>
        </label>
        <span className="price-filter__dash" aria-hidden="true">–</span>
        <label className="price-filter__field">
          <span>{t('price.maxShort')}</span>
          <span className="price-filter__input">
            <input type="number" inputMode="numeric" min={0} step={1} value={draft.max} aria-label={t('price.max')}
              onChange={(e) => update({ ...draft, max: e.target.value })} />
            <span aria-hidden="true">{unit}</span>
          </span>
        </label>
      </div>
      {bounds.max > bounds.min && (
        <div className="price-range" style={{ '--from': `${pct(draft.min)}%`, '--to': `${pct(draft.max)}%` }}>
          <span className="price-range__track" aria-hidden="true" />
          <input type="range" min={bounds.min} max={bounds.max} step={1} aria-label={t('price.min')}
            value={clamp(Number(draft.min) || bounds.min, bounds.min, bounds.max)}
            onChange={(e) => update({ ...draft, min: Math.min(Number(e.target.value), Number(draft.max) || bounds.max) })} />
          <input type="range" min={bounds.min} max={bounds.max} step={1} aria-label={t('price.max')}
            value={clamp(Number(draft.max) || bounds.max, bounds.min, bounds.max)}
            onChange={(e) => update({ ...draft, max: Math.max(Number(e.target.value), Number(draft.min) || bounds.min) })} />
        </div>
      )}
      {error && <p className="field__error" role="alert">{error}</p>}
      {onApply && <button type="submit" className="btn btn--outline price-range-box__apply">{t('price.apply')}</button>}
    </Tag>
  );
}
