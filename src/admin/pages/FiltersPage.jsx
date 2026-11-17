import { useState } from 'react';
import { ArrowDown, ArrowUp, Eye, EyeOff, Pencil, Plus, SlidersHorizontal, Trash2 } from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import { Badge, Button, Card, EmptyState, ErrorState, Field, Modal, Notice, PageHeader, SkeletonRows } from '../components/ui.jsx';
import { useApi, useTitle } from '../hooks.js';
import { can } from '../permissions.js';

/**
 * Admin → Filtres : groupes de filtres de la page produits (ex. « Mes solutions », « Zone d'application »,
 * « Type de peau ») et leurs valeurs. Les valeurs se cochent ensuite sur chaque fiche produit.
 * Créer, renommer (FR / AR), réordonner, masquer, supprimer. Propriétaire et Admin (le serveur vérifie aussi).
 */
export default function FiltersPage() {
  useTitle('Filtres');
  const { user } = useAuth();
  const editable = can(user, 'manageFilters');
  const { data, error, reload, setData } = useApi('/filters');
  const [editing, setEditing] = useState(null); // { kind: 'group'|'option', item?, group? }
  const [removing, setRemoving] = useState(null);
  const [message, setMessage] = useState(null);

  const run = async (fn, ok) => {
    setMessage(null);
    try {
      await fn();
      if (ok) setMessage({ tone: 'success', text: ok });
      reload();
    } catch (err) {
      setMessage({ tone: 'danger', text: err.message });
      reload();
    }
  };

  const moveGroup = (i, d) => {
    const list = [...data];
    [list[i], list[i + d]] = [list[i + d], list[i]];
    setData(list);
    run(() => admin.post('/filters/reorder', { ids: list.map((g) => g.id) }), 'Ordre des groupes enregistré.');
  };
  const moveOption = (gi, i, d) => {
    const groups = data.map((g) => ({ ...g, options: [...g.options] }));
    const list = groups[gi].options;
    [list[i], list[i + d]] = [list[i + d], list[i]];
    setData(groups);
    run(() => admin.post(`/filters/${groups[gi].id}/options/reorder`, { ids: list.map((o) => o.id) }), 'Ordre des valeurs enregistré.');
  };
  const toggle = (kind, item) => run(
    () => admin.patch(kind === 'group' ? `/filters/${item.id}` : `/filter-options/${item.id}`, { isActive: !item.isActive }),
    item.isActive ? `« ${item.name} » est masqué dans la boutique.` : `« ${item.name} » est de nouveau visible.`,
  );

  return (
    <div className="adm-page">
      <PageHeader title="Filtres" subtitle="Groupes de filtres de la page produits. Cochez ensuite les valeurs sur chaque fiche produit (carte « Filtres de la boutique »)."
        actions={editable && <Button icon={Plus} onClick={() => setEditing({ kind: 'group' })}>Nouveau groupe</Button>} />
      {message && <Notice tone={message.tone}>{message.text}</Notice>}
      {error && <ErrorState error={error} onRetry={reload} />}
      {!data && !error && <Card><SkeletonRows /></Card>}
      {data && data.length === 0 && (
        <Card>
          <EmptyState icon={SlidersHorizontal} title="Aucun groupe de filtres"
            text="Exemples : « Mes solutions » (Hydratation, Anti-taches…), « Zone d’application » (Visage, Yeux…), « Type de peau » (Sèche, Mixte…)."
            action={editable && <Button icon={Plus} onClick={() => setEditing({ kind: 'group' })}>Nouveau groupe</Button>} />
        </Card>
      )}
      {data && data.map((g, gi) => (
        <Card key={g.id} className={`adm-fgroup ${g.isActive ? '' : 'is-hidden'}`}
          title={(
            <span className="adm-fgroup__title">
              {g.name}
              {g.nameAr ? <span dir="rtl" lang="ar" className="adm-cat__ar">{g.nameAr}</span> : <span className="adm-cat__ar is-missing">Nom arabe à saisir</span>}
              {!g.isActive && <Badge tone="muted">Masqué</Badge>}
            </span>
          )}
          actions={editable && (
            <span className="adm-fgroup__actions">
              <Button variant="ghost" size="sm" icon={ArrowUp} aria-label={`Monter « ${g.name} »`} disabled={gi === 0} onClick={() => moveGroup(gi, -1)} />
              <Button variant="ghost" size="sm" icon={ArrowDown} aria-label={`Descendre « ${g.name} »`} disabled={gi === data.length - 1} onClick={() => moveGroup(gi, 1)} />
              <Button variant="ghost" size="sm" icon={Pencil} onClick={() => setEditing({ kind: 'group', item: g })}>Modifier</Button>
              <Button variant="ghost" size="sm" icon={g.isActive ? EyeOff : Eye} onClick={() => toggle('group', g)}>{g.isActive ? 'Masquer' : 'Afficher'}</Button>
              <Button variant="ghost" size="sm" icon={Trash2} aria-label={`Supprimer « ${g.name} »`} onClick={() => setRemoving({ kind: 'group', item: g })} />
            </span>
          )}>
          {g.options.length === 0 && <p className="adm-muted">Aucune valeur : le groupe n’apparaît pas dans la boutique.</p>}
          <ul className="adm-foptions">
            {g.options.map((o, i) => (
              <li key={o.id} className={`adm-foption ${o.isActive ? '' : 'is-hidden'}`}>
                <span className="adm-foption__name">
                  <strong>{o.name}</strong>
                  {o.nameAr ? <span dir="rtl" lang="ar" className="adm-cat__ar">{o.nameAr}</span> : <span className="adm-cat__ar is-missing">Nom arabe à saisir</span>}
                </span>
                <span className="adm-muted">{o.productCount} produit{o.productCount > 1 ? 's' : ''}</span>
                {!o.isActive && <Badge tone="muted">Masquée</Badge>}
                {editable && (
                  <span className="adm-foption__actions">
                    <Button variant="ghost" size="sm" icon={ArrowUp} aria-label={`Monter « ${o.name} »`} disabled={i === 0} onClick={() => moveOption(gi, i, -1)} />
                    <Button variant="ghost" size="sm" icon={ArrowDown} aria-label={`Descendre « ${o.name} »`} disabled={i === g.options.length - 1} onClick={() => moveOption(gi, i, 1)} />
                    <Button variant="ghost" size="sm" icon={Pencil} aria-label={`Modifier « ${o.name} »`} onClick={() => setEditing({ kind: 'option', item: o, group: g })} />
                    <Button variant="ghost" size="sm" icon={o.isActive ? EyeOff : Eye} aria-label={`${o.isActive ? 'Masquer' : 'Afficher'} « ${o.name} »`} onClick={() => toggle('option', o)} />
                    <Button variant="ghost" size="sm" icon={Trash2} aria-label={`Supprimer « ${o.name} »`} onClick={() => setRemoving({ kind: 'option', item: o })} />
                  </span>
                )}
              </li>
            ))}
          </ul>
          {editable && <Button variant="secondary" size="sm" icon={Plus} onClick={() => setEditing({ kind: 'option', group: g })}>Ajouter une valeur</Button>}
        </Card>
      ))}
      {editing && (
        <LabelDialog editing={editing} onClose={() => setEditing(null)}
          onSaved={(text) => { setEditing(null); setMessage({ tone: 'success', text }); reload(); }} />
      )}
      {removing && (
        <ConfirmDialog danger confirmLabel="Supprimer" onClose={() => setRemoving(null)}
          title={removing.kind === 'group' ? 'Supprimer le groupe ?' : 'Supprimer la valeur ?'}
          onConfirm={async () => {
            await admin.del(removing.kind === 'group' ? `/filters/${removing.item.id}` : `/filter-options/${removing.item.id}`);
            setMessage({ tone: 'success', text: `« ${removing.item.name} » a été supprimé.` });
            setRemoving(null);
            reload();
          }}>
          {removing.kind === 'group' ? (
            <p>« {removing.item.name} » et ses {removing.item.options.length} valeur(s) seront supprimés. Les produits restent intacts (seuls leurs filtres sont retirés).</p>
          ) : (
            <p>« {removing.item.name} » sera retirée de {removing.item.productCount} produit(s). Les produits restent intacts.</p>
          )}
          <p className="adm-muted">Pour la cacher temporairement, utilisez plutôt « Masquer ».</p>
        </ConfirmDialog>
      )}
    </div>
  );
}

function LabelDialog({ editing, onClose, onSaved }) {
  const { kind, item, group } = editing;
  const [form, setForm] = useState({ name: item?.name || '', nameAr: item?.nameAr || '', isActive: item?.isActive ?? true });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const title = item ? `Modifier « ${item.name} »` : kind === 'group' ? 'Nouveau groupe de filtres' : `Nouvelle valeur dans « ${group.name} »`;
  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      if (item) await admin.patch(kind === 'group' ? `/filters/${item.id}` : `/filter-options/${item.id}`, form);
      else if (kind === 'group') await admin.post('/filters', form);
      else await admin.post(`/filters/${group.id}/options`, form);
      onSaved(item ? `« ${form.name} » enregistré.` : `« ${form.name} » créé.`);
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  };
  return (
    <Modal open title={title} onClose={busy ? undefined : onClose}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Annuler</Button>
          <Button loading={busy} onClick={save}>Enregistrer</Button>
        </>
      )}>
      {error && !error.fields && <Notice tone="danger">{error.message}</Notice>}
      <Field label="Nom (français)" htmlFor="flt-name" required error={error?.fieldMessage?.('name')}
        hint={kind === 'group' ? 'Ex. « Mes solutions », « Zone d’application », « Type de peau ».' : 'Ex. « Hydratation », « Yeux », « Peau sèche ».'}>
        <input id="flt-name" className="adm-input" maxLength={80} value={form.name} autoFocus
          onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </Field>
      <Field label="Nom (arabe)" htmlFor="flt-name-ar" hint="Vide : le nom français s’affiche aussi en arabe." error={error?.fieldMessage?.('nameAr')}>
        <input id="flt-name-ar" className="adm-input" dir="rtl" lang="ar" maxLength={80} value={form.nameAr}
          onChange={(e) => setForm({ ...form, nameAr: e.target.value })} />
      </Field>
      <label className="adm-check">
        <input type="checkbox" checked={form.isActive} onChange={(e) => setForm({ ...form, isActive: e.target.checked })} />
        <span>Visible dans la boutique</span>
      </label>
    </Modal>
  );
}
