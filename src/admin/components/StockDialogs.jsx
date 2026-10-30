import { useState } from 'react';
import { admin } from '../api.js';
import { Badge, Button, Field, Modal, Notice } from './ui.jsx';

const variantName = (v) => (v.title && v.title !== 'Par défaut' ? `${v.productName} — ${v.title}` : v.productName);
const isInt = (s) => /^-?\d+$/.test(String(s).trim());

/**
 * Comptage, réception ou ajustement d'UNE variante. Envoie toujours POST /inventory/adjust :
 * le serveur applique la règle, enregistre le mouvement et refuse ce qui est invalide.
 */
export function AdjustDialog({ variant, mode, onClose, onDone }) {
  const unknown = variant.stockQuantity == null;
  const [kind, setKind] = useState(mode === 'adjust' ? 'damaged' : mode); // count | receive | damaged | recount | manual
  const [qty, setQty] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState({});

  const config = {
    count: { title: unknown ? 'Saisir le stock réel' : 'Recompter le stock', label: 'Quantité comptée', min: 0 },
    receive: { title: 'Réception de stock', label: 'Quantité reçue', min: 1 },
    damaged: { title: 'Retirer du stock', label: 'Quantité à retirer (abîmée, perdue…)', min: 1 },
    recount: { title: 'Recompter le stock', label: 'Nouvelle quantité comptée', min: 0 },
    manual: { title: 'Correction manuelle', label: 'Variation (+ pour ajouter, − pour retirer)', min: null },
  }[kind];

  const n = isInt(qty) ? Number(qty) : null;
  const after = n == null ? null
    : kind === 'count' || kind === 'recount' ? n
      : kind === 'receive' ? (variant.stockQuantity ?? 0) + n
        : kind === 'damaged' ? (variant.stockQuantity ?? 0) - n
          : (variant.stockQuantity ?? 0) + n;

  const submit = async (e) => {
    e.preventDefault();
    const local = {};
    if (n == null || (config.min != null && n < config.min) || (kind === 'manual' && n === 0)) {
      local.quantity = config.min === 1 ? 'Saisissez un nombre entier supérieur à 0.' : 'Saisissez un nombre entier valide.';
    }
    if (kind === 'manual' && !note.trim()) local.note = 'Expliquez la raison de cette correction.';
    setErrors(local);
    if (Object.keys(local).length) return;

    const body = {
      count: { mode: 'set', quantity: n, reason: unknown ? 'initial_count' : 'recount' },
      recount: { mode: 'set', quantity: n, reason: 'recount' },
      receive: { mode: 'delta', quantity: n, reason: 'restock' },
      damaged: { mode: 'delta', quantity: -n, reason: 'damaged' },
      manual: { mode: 'delta', quantity: n, reason: 'manual_adjustment' },
    }[kind];
    setBusy(true);
    try {
      const movement = await admin.post('/inventory/adjust', { variantId: variant.id, note: note.trim(), ...body });
      onDone(movement);
    } catch (err) {
      const quantity = err.fieldMessage('quantity');
      const noteError = err.fieldMessage('note');
      setErrors({ quantity, note: noteError, form: quantity || noteError ? null : err.message });
      setBusy(false);
    }
  };

  return (
    <Modal open title={config.title} onClose={onClose}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Annuler</Button>
          <Button type="submit" form="adm-adjust-form" loading={busy}>Enregistrer</Button>
        </>
      )}>
      <form id="adm-adjust-form" onSubmit={submit} noValidate>
        <p className="adm-modal__subject"><strong>{variantName(variant)}</strong>{variant.sku && <span className="adm-muted"> · {variant.sku}</span>}</p>
        <p className="adm-stock-now">Stock actuel : {unknown ? <Badge tone="neutral-dashed">Non renseigné</Badge> : <strong>{variant.stockQuantity}</strong>}</p>

        {mode === 'adjust' && (
          <fieldset className="adm-radio-group">
            <legend>Type d’ajustement</legend>
            <label><input type="radio" name="kind" checked={kind === 'damaged'} onChange={() => setKind('damaged')} /> Retirer (abîmé, perdu, cassé)</label>
            <label><input type="radio" name="kind" checked={kind === 'recount'} onChange={() => setKind('recount')} /> Recompter (inventaire)</label>
            <label><input type="radio" name="kind" checked={kind === 'manual'} onChange={() => setKind('manual')} /> Correction manuelle (note obligatoire)</label>
          </fieldset>
        )}

        <Field label={config.label} htmlFor="adm-qty" error={errors.quantity} required>
          <input id="adm-qty" className="adm-input adm-input--qty" inputMode="numeric" value={qty} autoComplete="off"
            onChange={(e) => setQty(e.target.value)} placeholder={kind === 'manual' ? 'ex. -2 ou 3' : '0'} />
        </Field>
        <Field label={kind === 'manual' ? 'Raison de la correction' : 'Note (facultative)'} htmlFor="adm-note" error={errors.note}
          hint={kind === 'receive' ? 'Ex. : fournisseur, n° de facture.' : null} required={kind === 'manual'}>
          <input id="adm-note" className="adm-input" maxLength={255} value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
        {after != null && (
          <p className={`adm-stock-preview ${after < 0 ? 'is-bad' : ''}`}>
            Après enregistrement : <strong>{after}</strong> {after < 0 && '— le stock ne peut pas devenir négatif'}
          </p>
        )}
        {errors.form && <Notice tone="danger">{errors.form}</Notice>}
      </form>
    </Modal>
  );
}

/** Saisie groupée du stock réel de toutes les variantes « non renseignées » (un mouvement par variante). */
export function BulkCountDialog({ variants, onClose, onDone }) {
  const [values, setValues] = useState({});
  const [results, setResults] = useState({});
  const [busy, setBusy] = useState(false);
  const filled = variants.filter((v) => (values[v.id] ?? '').trim() !== '');
  const invalid = filled.filter((v) => !/^\d+$/.test(values[v.id].trim()));

  const submit = async (e) => {
    e.preventDefault();
    if (!filled.length || invalid.length) return;
    setBusy(true);
    const next = {};
    for (const v of filled) {
      try {
        await admin.post('/inventory/adjust', {
          variantId: v.id, mode: 'set', quantity: Number(values[v.id]), reason: 'initial_count', note: 'Saisie d’inventaire',
        });
        next[v.id] = { ok: true };
      } catch (err) {
        next[v.id] = { ok: false, message: err.fieldMessage('quantity') || err.message };
      }
      setResults({ ...next });
    }
    setBusy(false);
    const okCount = Object.values(next).filter((r) => r.ok).length;
    onDone(okCount, Object.keys(next).length - okCount);
  };

  return (
    <Modal open size="lg" title="Saisie d’inventaire" onClose={busy ? undefined : onClose}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Fermer</Button>
          <Button type="submit" form="adm-bulk-form" loading={busy} disabled={!filled.length || invalid.length > 0}>
            Enregistrer {filled.length || ''} comptage{filled.length > 1 ? 's' : ''}
          </Button>
        </>
      )}>
      <p className="adm-muted">Comptez les articles en réserve et saisissez la quantité réelle. Laissez vide ce que vous n’avez pas encore compté.</p>
      <form id="adm-bulk-form" onSubmit={submit} noValidate>
        <table className="adm-table adm-table--compact adm-bulk">
          <thead><tr><th>Produit</th><th>SKU</th><th className="num">Quantité comptée</th><th aria-label="Résultat" /></tr></thead>
          <tbody>
            {variants.map((v) => {
              const value = values[v.id] ?? '';
              const bad = value.trim() !== '' && !/^\d+$/.test(value.trim());
              const result = results[v.id];
              return (
                <tr key={v.id}>
                  <td data-label="Produit">{variantName(v)}</td>
                  <td data-label="SKU">{v.sku || '—'}</td>
                  <td data-label="Quantité" className="num">
                    <input className={`adm-input adm-input--qty ${bad ? 'is-invalid' : ''}`} inputMode="numeric" value={value}
                      aria-label={`Quantité comptée pour ${variantName(v)}`} aria-invalid={bad} disabled={busy || result?.ok}
                      onChange={(e) => setValues((s) => ({ ...s, [v.id]: e.target.value }))} />
                  </td>
                  <td>
                    {bad && <span className="adm-field__error">Nombre entier ≥ 0</span>}
                    {result?.ok && <Badge tone="success">Enregistré</Badge>}
                    {result && !result.ok && <span className="adm-field__error">{result.message}</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </form>
    </Modal>
  );
}
