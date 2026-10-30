import { useState } from 'react';
import { AlertTriangle, ArrowDown, ArrowUp, Archive, CheckCircle2, Eye, Plus, RotateCcw, Zap } from 'lucide-react';
import { admin } from '../../api.js';
import ConfirmDialog from '../ConfirmDialog.jsx';
import { Badge, Button, Card } from '../ui.jsx';
import { PRODUCT_STATUS } from '../../format.js';

/** Statut + vérification avant activation (règles du serveur : activationErrors). */
export function StatusCard({ product, editable, dirty, onChanged, onPreview, toast }) {
  const [confirm, setConfirm] = useState(null);
  const [busy, setBusy] = useState(false);
  const errors = product.activationErrors;
  const change = async (status) => {
    setBusy(true);
    try {
      await admin.post(`/products/${product.id}/status`, { status });
      toast(`Produit ${PRODUCT_STATUS[status].label.toLowerCase()}`);
      onChanged();
    } catch (err) {
      toast(err.fieldMessage('status') || err.message, 'info');
    } finally {
      setBusy(false);
      setConfirm(null);
    }
  };
  const s = PRODUCT_STATUS[product.status];
  return (
    <Card title="Statut" actions={<Badge tone={s.tone}>{s.label}</Badge>}>
      <p className="adm-muted adm-status-text">
        {product.status === 'active' && 'Visible sur la boutique.'}
        {product.status === 'draft' && 'Invisible sur la boutique tant qu’il n’est pas activé.'}
        {product.status === 'archived' && 'Retiré de la boutique. Les commandes passées restent intactes.'}
      </p>
      {product.status !== 'active' && (
        <div className={`adm-checklist-box ${errors.length ? '' : 'is-ok'}`}>
          <p className="adm-checklist-box__title">
            {errors.length ? <><AlertTriangle size={15} aria-hidden="true" /> Avant activation</> : <><CheckCircle2 size={15} aria-hidden="true" /> Prêt à être activé</>}
          </p>
          {errors.length > 0 && <ul>{errors.map((e) => <li key={e}>{e}</li>)}</ul>}
        </div>
      )}
      <div className="adm-stack">
        <Button variant="secondary" icon={Eye} onClick={onPreview}>Aperçu de la fiche</Button>
        {editable && product.status !== 'active' && (
          <Button icon={Zap} loading={busy} disabled={errors.length > 0 || dirty} onClick={() => change('active')}
            title={dirty ? 'Enregistrez d’abord vos modifications' : undefined}>Activer</Button>
        )}
        {editable && product.status === 'active' && <Button variant="danger-ghost" icon={Archive} onClick={() => setConfirm('archived')}>Archiver</Button>}
        {editable && product.status !== 'draft' && <Button variant="ghost" icon={RotateCcw} loading={busy} onClick={() => setConfirm('draft')}>Repasser en brouillon</Button>}
      </div>
      {dirty && editable && product.status !== 'active' && <p className="adm-footnote adm-mt">Enregistrez vos modifications avant d’activer.</p>}
      {confirm && (
        <ConfirmDialog title={confirm === 'archived' ? 'Archiver ce produit ?' : 'Repasser en brouillon ?'} confirmLabel="Confirmer"
          onClose={() => setConfirm(null)} onConfirm={() => change(confirm)}>
          <p>Le produit ne sera plus visible sur la boutique. Les paniers des clients qui le contiennent l’ignoreront.</p>
        </ConfirmDialog>
      )}
    </Card>
  );
}

/** Catégories (la 1re est la principale : fil d'Ariane et badge de la fiche). */
export function CategoriesCard({ categories, value, onChange, editable, onCreated, toast }) {
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const selected = value.map((id) => categories.find((c) => c.id === id)).filter(Boolean);
  const others = categories.filter((c) => !value.includes(c.id));
  const move = (i, d) => {
    const next = [...value];
    [next[i], next[i + d]] = [next[i + d], next[i]];
    onChange(next);
  };
  const create = async () => {
    if (!name.trim()) return;
    setBusy(true);
    try {
      const c = await admin.post('/categories', { name: name.trim() });
      setName('');
      onCreated(c);
      onChange([...value, c.id]);
      toast(`Catégorie « ${c.name} » créée`);
    } catch (err) {
      toast(err.fieldMessage('name') || err.message, 'info');
    } finally {
      setBusy(false);
    }
  };
  return (
    <Card title="Catégories">
      {selected.length === 0 && <p className="adm-muted">Aucune catégorie (obligatoire pour activer).</p>}
      <ol className="adm-cat-list">
        {selected.map((c, i) => (
          <li key={c.id}>
            <span>{c.name} {i === 0 && <Badge tone="success">Principale</Badge>}</span>
            {editable && (
              <span className="adm-cat-list__tools">
                <button type="button" aria-label={`Monter ${c.name}`} disabled={i === 0} onClick={() => move(i, -1)}><ArrowUp size={14} /></button>
                <button type="button" aria-label={`Descendre ${c.name}`} disabled={i === selected.length - 1} onClick={() => move(i, 1)}><ArrowDown size={14} /></button>
                <button type="button" aria-label={`Retirer ${c.name}`} onClick={() => onChange(value.filter((x) => x !== c.id))}>×</button>
              </span>
            )}
          </li>
        ))}
      </ol>
      {editable && others.length > 0 && (
        <select className="adm-input adm-mt" value="" aria-label="Ajouter une catégorie" onChange={(e) => e.target.value && onChange([...value, Number(e.target.value)])}>
          <option value="">+ Ajouter une catégorie…</option>
          {others.map((c) => <option key={c.id} value={c.id}>{c.name}{c.isActive ? '' : ' (masquée)'}</option>)}
        </select>
      )}
      {editable && (
        <div className="adm-inline-create">
          <input className="adm-input" placeholder="Nouvelle catégorie" maxLength={100} value={name} aria-label="Nom de la nouvelle catégorie"
            onChange={(e) => setName(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); create(); } }} />
          <Button size="sm" variant="secondary" icon={Plus} loading={busy} onClick={create} aria-label="Créer la catégorie" />
        </div>
      )}
    </Card>
  );
}
