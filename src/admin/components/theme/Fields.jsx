import { useId } from 'react';
import { ArrowDown, ArrowUp, ImagePlus, Plus, RotateCcw, Trash2, X } from 'lucide-react';
import { SCHEMA } from '../../../theme/validate.js';
import { ASSET_LABELS, resolveImage } from '../../../theme/assets.js';
import { Button } from '../ui.jsx';

export const ICON_LABELS = {
  'hand-coins': 'Paiement', 'badge-check': 'Authenticité', truck: 'Livraison', headset: 'Service client', leaf: 'Nature',
  sparkles: 'Éclat', gift: 'Cadeau', 'shield-check': 'Sécurité', phone: 'Téléphone', heart: 'Cœur', package: 'Colis', clock: 'Délai',
};

function Counter({ value, max }) {
  if (!max) return null;
  const n = (value || '').length;
  return <span className={`adm-counter ${n > max ? 'is-over' : ''}`}>{n}/{max}</span>;
}

/** Un champ du schéma → le bon contrôle. `ctx` : produits, catégories, médias, sélecteur d'images, liens suggérés. */
export function Field({ field, value, onChange, error, disabled, ctx }) {
  const id = useId();
  const label = (
    <label htmlFor={id} className="adm-field__label">
      <span>{field.label}{field.required && <span aria-hidden="true"> *</span>}</span>
      {(field.type === 'text' || field.type === 'textarea') && <Counter value={value} max={field.maxLength} />}
    </label>
  );
  let control;
  switch (field.type) {
    case 'text':
      control = <input id={id} className="adm-input" value={value ?? ''} maxLength={field.maxLength} disabled={disabled} onChange={(e) => onChange(e.target.value)} />;
      break;
    case 'textarea':
      control = <textarea id={id} className="adm-input" rows={field.maxLength > 300 ? 6 : 3} value={value ?? ''} maxLength={field.maxLength} disabled={disabled} onChange={(e) => onChange(e.target.value)} />;
      break;
    case 'color':
      control = (
        <div className="adm-colorfield">
          <input type="color" aria-label={`${field.label} (sélecteur)`} value={/^#[0-9a-f]{6}$/i.test(value || '') ? value : '#000000'} disabled={disabled} onChange={(e) => onChange(e.target.value)} />
          <input id={id} className="adm-input" value={value ?? ''} maxLength={7} disabled={disabled} onChange={(e) => onChange(e.target.value.trim())} />
          {value !== field.default && !disabled && (
            <button type="button" className="adm-icon-btn" title="Couleur d’origine" aria-label={`Rétablir la couleur d’origine (${field.default})`} onClick={() => onChange(field.default)}><RotateCcw size={15} /></button>
          )}
        </div>
      );
      break;
    case 'select':
      control = (
        <select id={id} className="adm-input" value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
          {field.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      );
      break;
    case 'font':
      control = (
        <select id={id} className="adm-input" value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
          {Object.entries(SCHEMA.fonts).map(([key, f]) => <option key={key} value={key}>{f.label}</option>)}
        </select>
      );
      break;
    case 'icon':
      control = (
        <select id={id} className="adm-input" value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
          {SCHEMA.icons.map((key) => <option key={key} value={key}>{ICON_LABELS[key] || key}</option>)}
        </select>
      );
      break;
    case 'link':
      control = (
        <>
          <input id={id} className="adm-input" value={value ?? ''} list={`${id}-links`} placeholder={field.kinds?.length === 1 ? '/produits' : '/produits, #collection ou https://…'}
            disabled={disabled} onChange={(e) => onChange(e.target.value)} />
          <datalist id={`${id}-links`}>
            {(ctx.links || []).filter((l) => !field.kinds || field.kinds.some((k) => l.kind === k)).map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
          </datalist>
        </>
      );
      break;
    case 'product':
      control = (
        <select id={id} className="adm-input" value={value ?? ''} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
          {!field.required && <option value="">—</option>}
          {field.required && !value && <option value="">Choisir un produit…</option>}
          {(ctx.products || []).map((p) => <option key={p.slug} value={p.slug}>{p.name}{p.status !== 'active' ? ` (${p.status === 'draft' ? 'brouillon' : 'archivé'})` : ''}</option>)}
        </select>
      );
      break;
    case 'category':
      control = (
        <select id={id} className="adm-input" value={value ?? ''} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
          <option value="">Tous les produits</option>
          {(ctx.categories || []).map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
        </select>
      );
      break;
    case 'image': {
      const img = resolveImage(value, ctx.media);
      control = (
        <div className="adm-imagefield" id={id}>
          <div className="adm-imagefield__thumb">{img ? <img src={img.src} alt="" /> : <span className="adm-muted">Aucune image</span>}</div>
          <div className="adm-imagefield__meta">
            <span className="adm-muted">{value?.asset ? ASSET_LABELS[value.asset] : value?.mediaId ? `Médiathèque · n° ${value.mediaId}` : ''}</span>
            {!disabled && (
              <div className="adm-imagefield__actions">
                <Button size="sm" variant="secondary" icon={ImagePlus} onClick={() => ctx.pickImage((media) => onChange({ mediaId: media.id }))}>Choisir</Button>
                {field.assets?.length > 0 && value?.asset !== field.assets[0] && (
                  <Button size="sm" variant="ghost" icon={RotateCcw} onClick={() => onChange({ asset: field.assets[0] })}>Image d’origine</Button>
                )}
                {value && <Button size="sm" variant="ghost" icon={X} onClick={() => onChange(null)}>Retirer</Button>}
              </div>
            )}
          </div>
        </div>
      );
      break;
    }
    default:
      control = <p className="adm-field__error">Champ non pris en charge.</p>;
  }
  return (
    <div className={`adm-field ${error ? 'has-error' : ''}`}>
      {label}
      {control}
      {error && <p className="adm-field__error" role="alert">{error}</p>}
    </div>
  );
}

/** Formulaire généré : tous les champs d'une liste de définitions. */
export function FieldList({ fields, values, onChange, errors = {}, prefix, disabled, ctx }) {
  return fields.map((f) => (
    <Field key={f.id} field={f} value={values?.[f.id]} error={errors[`${prefix}.${f.id}`]} disabled={disabled} ctx={ctx}
      onChange={(v) => onChange({ ...values, [f.id]: v })} />
  ));
}

/** Liste d'éléments (liens, étapes, avantages, témoignages) : ajout, suppression, ordre. */
export function ItemsEditor({ def, items, onChange, errors, prefix, disabled, ctx, newItem }) {
  const move = (i, d) => {
    const next = [...items];
    [next[i], next[i + d]] = [next[i + d], next[i]];
    onChange(next);
  };
  return (
    <div className="adm-theme-items">
      <p className="adm-subtitle">{def.name}s <span className="adm-muted">({items.length}/{def.max})</span></p>
      {errors[`${prefix}`] && <p className="adm-field__error" role="alert">{errors[prefix]}</p>}
      {items.map((item, i) => (
        <div key={i} className="adm-theme-item">
          <div className="adm-theme-item__head">
            <strong>{def.name} {i + 1}</strong>
            {!disabled && (
              <div className="adm-theme-item__tools">
                <button type="button" aria-label={`Monter : ${def.name} ${i + 1}`} disabled={i === 0} onClick={() => move(i, -1)}><ArrowUp size={14} /></button>
                <button type="button" aria-label={`Descendre : ${def.name} ${i + 1}`} disabled={i === items.length - 1} onClick={() => move(i, 1)}><ArrowDown size={14} /></button>
                <button type="button" aria-label={`Supprimer : ${def.name} ${i + 1}`} disabled={items.length <= def.min} className="is-danger"
                  onClick={() => onChange(items.filter((_, j) => j !== i))}><Trash2 size={14} /></button>
              </div>
            )}
          </div>
          <FieldList fields={def.settings} values={item} errors={errors} prefix={`${prefix}.${i}`} disabled={disabled} ctx={ctx}
            onChange={(v) => onChange(items.map((it, j) => (j === i ? v : it)))} />
        </div>
      ))}
      {!disabled && items.length < def.max && (
        <Button size="sm" variant="secondary" icon={Plus} onClick={() => onChange([...items, newItem()])}>Ajouter : {def.name.toLowerCase()}</Button>
      )}
    </div>
  );
}
