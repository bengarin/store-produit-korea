import { ArrowDown, ArrowUp, Plus, Trash2 } from 'lucide-react';
import NamedIcon from '../../../components/NamedIcon.jsx';
import { Button } from '../ui.jsx';

export const ICONS = [
  ['leaf', 'Feuille'], ['droplets', 'Gouttes'], ['sparkles', 'Éclat'], ['sun', 'Soleil'], ['citrus', 'Agrume'],
  ['eye', 'Œil'], ['clock', 'Horloge'], ['layers', 'Couches'], ['flask', 'Flacon'], ['hand', 'Main'],
];

/** Pictos de la fiche : icône choisie dans une liste fermée + libellé court (8 maximum). */
export function HighlightsEditor({ value, onChange, disabled }) {
  const update = (i, patch) => onChange(value.map((h, j) => (j === i ? { ...h, ...patch } : h)));
  const move = (i, d) => {
    const next = [...value];
    [next[i], next[i + d]] = [next[i + d], next[i]];
    onChange(next);
  };
  return (
    <div className="adm-highlights">
      {value.map((h, i) => (
        <div key={i} className="adm-highlight">
          <span className="adm-highlight__icon" aria-hidden="true"><NamedIcon name={h.icon} size={20} strokeWidth={1.5} /></span>
          <select className="adm-input" value={h.icon} disabled={disabled} aria-label={`Icône du picto ${i + 1}`} onChange={(e) => update(i, { icon: e.target.value })}>
            {ICONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <input className="adm-input" maxLength={60} value={h.label} disabled={disabled} aria-label={`Texte du picto ${i + 1}`}
            placeholder="ex. Texture gel" onChange={(e) => update(i, { label: e.target.value })} />
          {!disabled && (
            <span className="adm-highlight__tools">
              <button type="button" aria-label="Monter" disabled={i === 0} onClick={() => move(i, -1)}><ArrowUp size={14} /></button>
              <button type="button" aria-label="Descendre" disabled={i === value.length - 1} onClick={() => move(i, 1)}><ArrowDown size={14} /></button>
              <button type="button" aria-label={`Supprimer le picto ${i + 1}`} onClick={() => onChange(value.filter((_, j) => j !== i))}><Trash2 size={14} /></button>
            </span>
          )}
        </div>
      ))}
      {!disabled && value.length < 8 && (
        <Button size="sm" variant="secondary" icon={Plus} onClick={() => onChange([...value, { icon: 'leaf', label: '' }])}>Ajouter un picto</Button>
      )}
    </div>
  );
}

/** Liste de phrases saisie « une par ligne » (ingrédients, bienfaits, étapes). */
export function LinesField({ id, value, onChange, disabled, rows = 5, placeholder }) {
  return (
    <textarea id={id} className="adm-input" rows={rows} value={value} disabled={disabled} placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)} />
  );
}

export const linesToList = (text) => text.split('\n').map((l) => l.trim()).filter(Boolean);
export const listToLines = (list) => (list || []).join('\n');
