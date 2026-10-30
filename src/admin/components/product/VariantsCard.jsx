import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Boxes, Layers, Plus, Save, Trash2, Wand2, X } from 'lucide-react';
import { admin } from '../../api.js';
import ConfirmDialog from '../ConfirmDialog.jsx';
import { Badge, Button, Card, Field, Notice } from '../ui.jsx';

const FIELDS = ['price', 'compareAtPrice', 'cost', 'sku', 'barcode', 'lowStockThreshold', 'allowBackorder', 'trackInventory'];
const toForm = (v) => Object.fromEntries(FIELDS.filter((k) => k in v).map((k) => [k, v[k] ?? (typeof v[k] === 'boolean' ? false : '')]));
const emptyToNull = (value) => (value === '' ? null : value);

function StockInfo({ v, productName }) {
  if (!v.trackInventory) return <span className="adm-muted">Non suivi</span>;
  return (
    <span className="adm-stock-inline">
      {v.stockQuantity == null ? <Badge tone="neutral-dashed">Non renseigné</Badge> : <strong>{v.stockQuantity}</strong>}
      <Link to={`/admin/inventory?search=${encodeURIComponent(productName)}`} className="adm-link" title="Le stock se gère dans la page Stock">
        <Boxes size={13} aria-hidden="true" /> Gérer
      </Link>
    </span>
  );
}

/** Formulaire d'une variante (prix, références, réglages). Le stock n'est JAMAIS modifiable ici. */
function VariantForm({ variant, productName, editable, canEditCost, onSaved, toast, compact }) {
  const initial = useMemo(() => toForm(variant), [variant]);
  const [form, setForm] = useState(initial);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const changed = FIELDS.filter((k) => k in form && String(form[k] ?? '') !== String(initial[k] ?? ''));
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));

  const save = async (e) => {
    e?.preventDefault();
    if (!changed.length) return;
    setBusy(true);
    setErrors({});
    try {
      const body = Object.fromEntries(changed.map((k) => [k, ['compareAtPrice', 'cost', 'sku', 'barcode'].includes(k) ? emptyToNull(form[k]) : form[k]]));
      const saved = await admin.patch(`/variants/${variant.id}`, body);
      toast(compact ? `Variante « ${saved.title} » enregistrée` : 'Prix et références enregistrés');
      onSaved();
    } catch (err) {
      setErrors({ ...Object.fromEntries(FIELDS.map((k) => [k, err.fieldMessage(k)])), form: err.fields ? (err.fieldMessage('status') || null) : err.message });
    } finally {
      setBusy(false);
    }
  };

  const id = (k) => `v${variant.id}-${k}`;
  const input = (k, label, props = {}) => (
    <Field label={label} htmlFor={id(k)} error={errors[k]}>
      <input id={id(k)} className="adm-input" value={form[k] ?? ''} onChange={set(k)} disabled={!editable || (k === 'cost' && !canEditCost)} {...props} />
    </Field>
  );

  return (
    <form className={`adm-variant ${compact ? 'adm-variant--row' : ''}`} onSubmit={save} noValidate>
      {compact && (
        <div className="adm-variant__title">
          <strong>{variant.title}</strong>
          {variant.isDefault && <Badge tone="success">Par défaut</Badge>}
        </div>
      )}
      <div className="adm-variant__grid">
        {input('price', 'Prix de vente (DH)', { inputMode: 'decimal' })}
        {input('compareAtPrice', 'Prix comparatif (DH)', { inputMode: 'decimal', placeholder: 'Facultatif' })}
        {'cost' in form && input('cost', 'Coût d’achat (DH)', { inputMode: 'decimal', placeholder: 'Interne' })}
        {input('sku', 'SKU', { maxLength: 64, placeholder: 'ex. MPC-ALOE-250' })}
        {input('barcode', 'Code-barres (EAN)', { maxLength: 64 })}
        {input('lowStockThreshold', 'Seuil d’alerte', { inputMode: 'numeric' })}
        <div className="adm-field">
          <span className="adm-field__label">Stock</span>
          <StockInfo v={variant} productName={productName} />
        </div>
      </div>
      <div className="adm-variant__flags">
        <label className="adm-check"><input type="checkbox" checked={!!form.trackInventory} onChange={set('trackInventory')} disabled={!editable} /> Suivre le stock</label>
        <label className="adm-check"><input type="checkbox" checked={!!form.allowBackorder} onChange={set('allowBackorder')} disabled={!editable} /> Vendre même sans stock</label>
      </div>
      {errors.form && <Notice tone="danger">{errors.form}</Notice>}
      {editable && changed.length > 0 && (
        <div className="adm-variant__actions">
          <Button type="submit" size="sm" icon={Save} loading={busy}>Enregistrer</Button>
          <Button size="sm" variant="ghost" onClick={() => { setForm(initial); setErrors({}); }}>Annuler</Button>
        </div>
      )}
    </form>
  );
}

function OptionsEditor({ product, onSaved, onCancel, toast }) {
  const [options, setOptions] = useState(product.options.length ? product.options.map((o) => ({ name: o.name, values: [...o.values], draft: '' })) : [{ name: '', values: [], draft: '' }]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const update = (i, patch) => setOptions((list) => list.map((o, j) => (j === i ? { ...o, ...patch } : o)));
  const addValue = (i) => {
    const value = options[i].draft.trim();
    if (!value) return;
    if (options[i].values.some((v) => v.toLowerCase() === value.toLowerCase())) return update(i, { draft: '' });
    update(i, { values: [...options[i].values, value], draft: '' });
  };
  const save = async () => {
    const payload = options.map((o) => ({ name: o.name.trim(), values: [...o.values, ...(o.draft.trim() ? [o.draft.trim()] : [])] }))
      .filter((o) => o.name || o.values.length);
    setBusy(true);
    setError('');
    try {
      await admin.put(`/products/${product.id}/options`, payload);
      toast('Options enregistrées');
      onSaved();
    } catch (err) {
      setError(err.fieldMessage('options') || err.fieldMessage('status') || err.message);
      setBusy(false);
    }
  };
  return (
    <div className="adm-options-editor">
      {options.map((o, i) => (
        <div key={i} className="adm-option">
          <Field label={`Option ${i + 1}`} htmlFor={`opt-${i}`}>
            <input id={`opt-${i}`} className="adm-input" maxLength={50} placeholder="ex. Contenance, Teinte" value={o.name} onChange={(e) => update(i, { name: e.target.value })} />
          </Field>
          <div className="adm-field">
            <label htmlFor={`optv-${i}`}>Valeurs</label>
            <div className="adm-tags">
              {o.values.map((v) => (
                <span key={v} className="adm-tag">{v}
                  <button type="button" aria-label={`Retirer ${v}`} onClick={() => update(i, { values: o.values.filter((x) => x !== v) })}><X size={12} /></button>
                </span>
              ))}
              <input id={`optv-${i}`} className="adm-tags__input" maxLength={50} placeholder="Ajouter puis Entrée" value={o.draft}
                onChange={(e) => update(i, { draft: e.target.value })}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addValue(i); } }} />
            </div>
          </div>
          <Button size="sm" variant="ghost" icon={Trash2} aria-label={`Supprimer l’option ${o.name || i + 1}`} onClick={() => setOptions((list) => list.filter((_, j) => j !== i))} />
        </div>
      ))}
      {options.length < 3 && <Button size="sm" variant="secondary" icon={Plus} onClick={() => setOptions((l) => [...l, { name: '', values: [], draft: '' }])}>Ajouter une option</Button>}
      <Notice tone="info">Une nouvelle option s’applique aux variantes existantes avec sa première valeur. Une valeur encore utilisée par une variante ne peut pas être retirée.</Notice>
      {error && <Notice tone="danger">{error}</Notice>}
      <div className="adm-variant__actions">
        <Button icon={Save} loading={busy} onClick={save}>Enregistrer les options</Button>
        <Button variant="ghost" onClick={onCancel}>Annuler</Button>
      </div>
    </div>
  );
}

function NewVariant({ product, onSaved, toast }) {
  const [values, setValues] = useState(Object.fromEntries(product.options.map((o) => [o.name, o.values[0]])));
  const [price, setPrice] = useState(String(product.variants.find((v) => v.isDefault)?.price ?? ''));
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const add = async () => {
    setBusy(true);
    setError('');
    try {
      await admin.post(`/products/${product.id}/variants`, { optionValues: values, price });
      toast('Variante ajoutée');
      onSaved();
    } catch (err) {
      setError(err.fieldMessage('optionValues') || err.fieldMessage('price') || err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="adm-new-variant">
      {product.options.map((o) => (
        <Field key={o.name} label={o.name} htmlFor={`nv-${o.name}`}>
          <select id={`nv-${o.name}`} className="adm-input" value={values[o.name]} onChange={(e) => setValues((v) => ({ ...v, [o.name]: e.target.value }))}>
            {o.values.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </Field>
      ))}
      <Field label="Prix (DH)" htmlFor="nv-price">
        <input id="nv-price" className="adm-input" inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} />
      </Field>
      <Button icon={Plus} loading={busy} onClick={add}>Ajouter la variante</Button>
      {error && <p className="adm-field__error adm-new-variant__error" role="alert">{error}</p>}
    </div>
  );
}

export default function VariantsCard({ product, editable, canEditCost, onChanged, toast }) {
  const [editingOptions, setEditingOptions] = useState(false);
  const [toDelete, setToDelete] = useState(null);
  const [generating, setGenerating] = useState(false);
  const hasOptions = product.options.length > 0;
  const productName = product.displayName || `${product.brand} ${product.name}`;
  const refresh = () => { setEditingOptions(false); onChanged(); };

  const missing = useMemo(() => {
    if (!hasOptions) return [];
    const combos = product.options.reduce((acc, o) => acc.flatMap((c) => o.values.map((v) => ({ ...c, [o.name]: v }))), [{}]);
    const existing = new Set(product.variants.map((v) => JSON.stringify(product.options.map((o) => v.options[o.name]))));
    return combos.filter((c) => !existing.has(JSON.stringify(product.options.map((o) => c[o.name]))));
  }, [product, hasOptions]);

  const generate = async () => {
    setGenerating(true);
    const price = product.variants.find((v) => v.isDefault)?.price ?? 0;
    let created = 0;
    for (const optionValues of missing) {
      try {
        await admin.post(`/products/${product.id}/variants`, { optionValues, price });
        created += 1;
      } catch (err) {
        toast(err.message, 'info');
      }
    }
    setGenerating(false);
    toast(`${created} variante${created > 1 ? 's' : ''} créée${created > 1 ? 's' : ''} (au prix de la variante par défaut)`);
    onChanged();
  };

  if (!hasOptions && !editingOptions) {
    const v = product.variants[0];
    return (
      <Card title="Prix et références" actions={editable && <Button size="sm" variant="ghost" icon={Layers} onClick={() => setEditingOptions(true)}>Ajouter des options</Button>}>
        {v && <VariantForm key={`${v.id}-${JSON.stringify(v)}`} variant={v} productName={productName} editable={editable} canEditCost={canEditCost} onSaved={onChanged} toast={toast} />}
        <p className="adm-footnote">Le prix comparatif est enregistré mais pas encore affiché sur la boutique (évolution prévue).</p>
      </Card>
    );
  }

  return (
    <Card title="Options et variantes" actions={editable && !editingOptions && <Button size="sm" variant="ghost" icon={Layers} onClick={() => setEditingOptions(true)}>Modifier les options</Button>}>
      {editingOptions ? (
        <OptionsEditor product={product} onSaved={refresh} onCancel={() => setEditingOptions(false)} toast={toast} />
      ) : (
        <>
          <p className="adm-muted">
            {product.options.map((o) => `${o.name} : ${o.values.join(', ')}`).join(' · ')}
          </p>
          <div className="adm-variants">
            {product.variants.map((v) => (
              <div key={v.id} className="adm-variants__item">
                <VariantForm key={`${v.id}-${JSON.stringify(v)}`} variant={v} productName={productName} editable={editable} canEditCost={canEditCost} onSaved={onChanged} toast={toast} compact />
                {editable && (
                  <div className="adm-variants__side">
                    {!v.isDefault && (
                      <Button size="sm" variant="ghost" onClick={async () => {
                        try { await admin.patch(`/variants/${v.id}`, { isDefault: true }); toast('Variante par défaut modifiée'); onChanged(); } catch (err) { toast(err.message, 'info'); }
                      }}>Définir par défaut</Button>
                    )}
                    {product.variants.length > 1 && <Button size="sm" variant="danger-ghost" icon={Trash2} aria-label={`Supprimer la variante ${v.title}`} onClick={() => setToDelete(v)} />}
                  </div>
                )}
              </div>
            ))}
          </div>
          {editable && missing.length > 0 && (
            <Notice tone="info" icon={Wand2} action={<Button size="sm" variant="secondary" loading={generating} onClick={generate}>Créer les {missing.length} manquantes</Button>}>
              {missing.length} combinaison{missing.length > 1 ? 's' : ''} sans variante.
            </Notice>
          )}
          {editable && <NewVariant key={product.variants.length} product={product} onSaved={onChanged} toast={toast} />}
          <p className="adm-footnote">La boutique vend pour l’instant la variante <strong>par défaut</strong> : le choix de variante sur la fiche publique n’existe pas encore (évolution prévue).</p>
        </>
      )}
      {toDelete && (
        <ConfirmDialog title="Supprimer cette variante ?" confirmLabel="Supprimer" danger onClose={() => setToDelete(null)}
          onConfirm={async () => { await admin.del(`/variants/${toDelete.id}`); setToDelete(null); toast('Variante supprimée'); onChanged(); }}>
          <p>La variante <strong>{toDelete.title}</strong> sera supprimée. Une variante déjà commandée ou avec un historique de stock ne peut pas l’être.</p>
        </ConfirmDialog>
      )}
    </Card>
  );
}
