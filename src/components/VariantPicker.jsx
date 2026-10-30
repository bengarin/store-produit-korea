import { matchVariant, variantStatus } from '../utils/variants.js';

const STATE_TEXT = { out_of_stock: 'épuisé', unavailable: 'indisponible', missing: 'combinaison indisponible' };

/**
 * Choix des options (contenance, teinte…). Chaque valeur indique si la combinaison existe et si elle est
 * disponible ; choisir une valeur sans combinaison exacte bascule vers la variante la plus proche.
 */
export default function VariantPicker({ product, variant, onChange }) {
  const selection = variant?.options || {};

  const stateOf = (name, value) => {
    const candidate = matchVariant(product, { ...selection, [name]: value });
    return candidate ? variantStatus(product, candidate) : 'missing';
  };

  const choose = (name, value) => {
    const exact = matchVariant(product, { ...selection, [name]: value });
    if (exact) return onChange(exact);
    // Pas de variante pour cette combinaison : la plus proche ayant cette valeur (disponible d'abord).
    const score = (v) =>
      (variantStatus(product, v) === 'available' ? 100 : 0) +
      product.options.filter((o) => v.options[o.name] === selection[o.name]).length;
    const best = product.variants.filter((v) => v.options[name] === value).sort((a, b) => score(b) - score(a))[0];
    if (best) onChange(best);
  };

  return (
    <div className="pdp-options">
      {product.options.map((option) => (
        <fieldset className="pdp-option" key={option.name}>
          <legend className="pdp-option__label">
            {option.name} : <strong>{selection[option.name] || '—'}</strong>
          </legend>
          <div className="pdp-option__values">
            {option.values.map((value) => {
              const exists = product.variants.some((v) => v.options[option.name] === value);
              if (!exists) return null;
              const state = stateOf(option.name, value);
              const selected = selection[option.name] === value;
              return (
                <button
                  key={value}
                  type="button"
                  className={`pdp-option__value ${selected ? 'is-selected' : ''} ${state !== 'available' ? 'is-unavailable' : ''}`}
                  aria-pressed={selected}
                  aria-label={state === 'available' ? value : `${value} (${STATE_TEXT[state]})`}
                  onClick={() => choose(option.name, value)}
                >
                  {value}
                </button>
              );
            })}
          </div>
        </fieldset>
      ))}
    </div>
  );
}
