import { useId, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { useCatalog } from '../context/CatalogContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';
import PriceRange from './PriceRange.jsx';

function Section({ title, defaultOpen = true, children, badge = 0 }) {
  const id = useId();
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className={`filter-section ${open ? 'is-open' : ''}`}>
      <h3 className="filter-section__head">
        <button type="button" aria-expanded={open} aria-controls={`${id}-body`} onClick={() => setOpen((o) => !o)}>
          <span>{title}{badge > 0 && <span className="filter-section__badge">{badge}</span>}</span>
          <ChevronDown size={18} aria-hidden="true" className="filter-section__chevron" />
        </button>
      </h3>
      <div id={`${id}-body`} className="filter-section__body" hidden={!open}>{children}</div>
    </section>
  );
}

/**
 * Contenu des filtres (barre latérale sur ordinateur, tiroir sur mobile) : catégories, prix, puis les groupes
 * créés dans Admin → Filtres. `live` : chaque choix s'applique tout de suite (prix : bouton « Appliquer ») ;
 * sinon les choix restent en brouillon jusqu'à « Appliquer » du tiroir.
 */
export default function FilterPanel({ state, onChange, bounds, counts, categoryCounts, live }) {
  const { categoryTree, filterGroups } = useCatalog();
  const { t, tc } = useI18n();
  const name = useId();

  const toggleOption = (group, option) => {
    const list = state.options[group] || [];
    const next = list.includes(option) ? list.filter((o) => o !== option) : [...list, option];
    const options = { ...state.options, [group]: next };
    if (!next.length) delete options[group];
    onChange({ ...state, options });
  };

  const categoryRow = (cat, sub = false) => {
    const count = categoryCounts[cat.id] ?? 0;
    return (
      <label key={cat.id} className={`filter-option ${sub ? 'filter-option--sub' : ''} ${count === 0 && state.category !== cat.id ? 'is-empty' : ''}`}>
        <input type="radio" name={`${name}-cat`} checked={state.category === cat.id} onChange={() => onChange({ ...state, category: cat.id })} />
        <span className="filter-option__label">{tc(cat.label)}</span>
        <span className="filter-option__count">{count}</span>
      </label>
    );
  };

  return (
    <div className="filter-panel">
      {categoryTree.length > 0 && (
        <Section title={t('nav.categories')} badge={state.category !== 'all' ? 1 : 0}>
          <label className="filter-option">
            <input type="radio" name={`${name}-cat`} checked={state.category === 'all'} onChange={() => onChange({ ...state, category: 'all' })} />
            <span className="filter-option__label">{t('grid.all')}</span>
            <span className="filter-option__count">{categoryCounts.all ?? 0}</span>
          </label>
          {categoryTree.map((cat) => [categoryRow(cat), ...cat.children.map((c) => categoryRow(c, true))])}
        </Section>
      )}
      {bounds.max > 0 && (
        <Section title={t('price.title')} badge={state.price ? 1 : 0}>
          <PriceRange bounds={bounds} value={state.price}
            onApply={live ? (price) => onChange({ ...state, price }) : undefined}
            onDraft={live ? undefined : (price) => onChange({ ...state, price })} />
        </Section>
      )}
      {filterGroups.map((g, i) => {
        const selected = state.options[g.id] || [];
        return (
          <Section key={g.id} title={tc(g.label)} badge={selected.length} defaultOpen={i < 2 || selected.length > 0}>
            {g.options.map((o) => {
              const count = counts[`${g.id}:${o.id}`] ?? 0;
              const checked = selected.includes(o.id);
              return (
                <label key={o.id} className={`filter-option ${count === 0 && !checked ? 'is-empty' : ''}`}>
                  <input type="checkbox" checked={checked} onChange={() => toggleOption(g.id, o.id)} />
                  <span className="filter-option__label">{tc(o.label)}</span>
                  <span className="filter-option__count">{count}</span>
                </label>
              );
            })}
          </Section>
        );
      })}
    </div>
  );
}
