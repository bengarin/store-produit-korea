import { useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, Eye, EyeOff, FolderTree, Package, Pencil, Plus, Trash2 } from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import { Badge, Button, Card, EmptyState, ErrorState, Field, Modal, Notice, PageHeader, SkeletonRows } from '../components/ui.jsx';
import { PRODUCT_STATUS } from '../format.js';
import { useApi, useTitle } from '../hooks.js';
import { can } from '../permissions.js';

/** Catégories principales (ordre du menu), chacune avec ses sous-catégories. */
function toTree(list) {
  const sorted = [...list].sort((a, b) => a.position - b.position || a.id - b.id);
  const tops = sorted.filter((c) => !c.parentId).map((c) => ({ ...c, children: [] }));
  const byId = new Map(tops.map((c) => [c.id, c]));
  const orphans = [];
  sorted.filter((c) => c.parentId).forEach((c) => (byId.get(c.parentId) ? byId.get(c.parentId).children.push(c) : orphans.push(c)));
  return [...tops, ...orphans.map((c) => ({ ...c, children: [] }))];
}

/** Ordre complet envoyé au serveur : chaque catégorie suivie de ses sous-catégories. */
const flatIds = (tree) => tree.flatMap((c) => [c.id, ...c.children.map((x) => x.id)]);

/**
 * Admin → Catégories : catégories et sous-catégories du menu « Catégories » de la boutique.
 * Créer, renommer (FR / AR), rattacher à une catégorie parente, réordonner, masquer, associer des produits.
 * Réservé aux rôles Propriétaire et Admin (le serveur vérifie aussi).
 */
export default function CategoriesPage() {
  useTitle('Catégories');
  const { user } = useAuth();
  const editable = can(user, 'manageCategories');
  const { data, error, reload, setData } = useApi('/categories');
  const [editing, setEditing] = useState(null); // {} = nouvelle catégorie ; {parentId} = nouvelle sous-catégorie
  const [linking, setLinking] = useState(null);
  const [removing, setRemoving] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);
  const tree = useMemo(() => (data ? toTree(data) : []), [data]);

  const run = async (fn, ok) => {
    setBusy(true);
    setMessage(null);
    try {
      await fn();
      if (ok) setMessage({ tone: 'success', text: ok });
      reload();
    } catch (err) {
      setMessage({ tone: 'danger', text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const move = (siblings, index, delta, parentIndex = null) => {
    const target = index + delta;
    if (target < 0 || target >= siblings.length) return;
    const next = tree.map((c) => ({ ...c, children: [...c.children] }));
    const list = parentIndex === null ? next : next[parentIndex].children;
    [list[index], list[target]] = [list[target], list[index]];
    const ids = flatIds(next);
    // Affichage immédiat, puis enregistrement.
    setData(data.map((c) => ({ ...c, position: ids.indexOf(c.id) })));
    run(() => admin.post('/categories/reorder', { ids }), 'Ordre enregistré.');
  };

  const toggleVisible = (cat) =>
    run(() => admin.patch(`/categories/${cat.id}`, { isActive: !cat.isActive }),
      cat.isActive ? `« ${cat.name} » est masquée du menu.` : `« ${cat.name} » est de nouveau visible.`);

  const row = (cat, siblings, index, parentIndex = null) => {
    const sub = parentIndex !== null || Boolean(cat.parentId);
    const parentHidden = sub && tree[parentIndex]?.isActive === false;
    return (
      <li key={cat.id} className={`adm-cat ${sub ? 'adm-cat--sub' : ''} ${cat.isActive ? '' : 'is-hidden'}`}>
        <div className="adm-cat__main">
          <span className="adm-cat__name">
            <strong>{cat.name}</strong>
            {cat.nameAr ? <span dir="rtl" lang="ar" className="adm-cat__ar">{cat.nameAr}</span> : <span className="adm-cat__ar is-missing">Nom arabe à saisir</span>}
          </span>
          <span className="adm-cat__meta">
            <Badge tone="neutral">{cat.productCount} produit{cat.productCount > 1 ? 's' : ''}</Badge>
            {!cat.isActive && <Badge tone="warning">Masquée</Badge>}
            {cat.isActive && parentHidden && <Badge tone="muted">Masquée avec sa catégorie</Badge>}
          </span>
        </div>
        {editable && (
          <div className="adm-cat__actions">
            <Button variant="ghost" size="sm" icon={ArrowUp} aria-label={`Monter « ${cat.name} »`} title="Monter"
              disabled={busy || index === 0} onClick={() => move(siblings, index, -1, parentIndex)} />
            <Button variant="ghost" size="sm" icon={ArrowDown} aria-label={`Descendre « ${cat.name} »`} title="Descendre"
              disabled={busy || index === siblings.length - 1} onClick={() => move(siblings, index, 1, parentIndex)} />
            <Button variant="ghost" size="sm" icon={Pencil} onClick={() => setEditing(cat)}>Modifier</Button>
            <Button variant="ghost" size="sm" icon={Package} onClick={() => setLinking(cat)}>Produits</Button>
            <Button variant="ghost" size="sm" icon={cat.isActive ? EyeOff : Eye} disabled={busy} onClick={() => toggleVisible(cat)}>
              {cat.isActive ? 'Masquer' : 'Afficher'}
            </Button>
            {!sub && (
              <Button variant="ghost" size="sm" icon={Plus} onClick={() => setEditing({ parentId: cat.id })}>Sous-catégorie</Button>
            )}
            <Button variant="ghost" size="sm" icon={Trash2} aria-label={`Supprimer « ${cat.name} »`} title="Supprimer"
              onClick={() => setRemoving(cat)} />
          </div>
        )}
      </li>
    );
  };

  return (
    <div className="adm-page">
      <PageHeader
        title="Catégories"
        subtitle="Catégories et sous-catégories du menu « Catégories » de la boutique. L'ordre ici est l'ordre du menu."
        actions={editable && <Button icon={Plus} onClick={() => setEditing({})}>Nouvelle catégorie</Button>}
      />
      {!editable && <Notice tone="info">Lecture seule : seuls les rôles Propriétaire et Admin modifient les catégories.</Notice>}
      <Notice tone="info">
        Une catégorie masquée disparaît du menu avec ses sous-catégories. Ses produits restent dans l'administration
        et sur leurs fiches.
      </Notice>
      {message && <Notice tone={message.tone}>{message.text}</Notice>}
      <Card padded={false}>
        {error && <ErrorState error={error} onRetry={reload} />}
        {!data && !error && <SkeletonRows rows={6} />}
        {data && tree.length === 0 && <EmptyState icon={FolderTree} title="Aucune catégorie" text="Créez la première catégorie du menu." />}
        {tree.length > 0 && (
          <ul className="adm-cats">
            {tree.map((cat, i) => (
              <li key={cat.id} className="adm-cats__group">
                <ul>{row(cat, tree, i)}</ul>
                {cat.children.length > 0 && <ul className="adm-cats__subs">{cat.children.map((c, j) => row(c, cat.children, j, i))}</ul>}
              </li>
            ))}
          </ul>
        )}
      </Card>

      {editing && (
        <CategoryDialog category={editing} tops={tree.filter((c) => !c.parentId)} onClose={() => setEditing(null)}
          onSaved={(text) => { setEditing(null); setMessage({ tone: 'success', text }); reload(); }} />
      )}
      {linking && (
        <ProductsDialog category={linking} onClose={() => setLinking(null)}
          onSaved={(text) => { setLinking(null); setMessage({ tone: 'success', text }); reload(); }} />
      )}
      {removing && (
        <ConfirmDialog title={`Supprimer « ${removing.name} » ?`} danger confirmLabel="Supprimer"
          onClose={() => setRemoving(null)}
          onConfirm={async () => {
            await admin.del(`/categories/${removing.id}`);
            setRemoving(null);
            setMessage({ tone: 'success', text: `« ${removing.name} » a été supprimée.` });
            reload();
          }}>
          <p>Suppression définitive. Pour la retirer du menu sans la supprimer, utilisez plutôt « Masquer ».</p>
          <p>Impossible si elle contient encore des produits ou des sous-catégories.</p>
        </ConfirmDialog>
      )}
    </div>
  );
}

/** Créer / modifier : nom FR, nom AR, catégorie parente, visibilité. */
function CategoryDialog({ category, tops, onClose, onSaved }) {
  const isNew = !category.id;
  const hasChildren = tops.some((c) => c.id === category.id && c.children.length > 0);
  const [form, setForm] = useState({
    name: category.name || '',
    nameAr: category.nameAr || '',
    parentId: category.parentId ?? null,
    isActive: category.isActive ?? true,
  });
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));

  const save = async () => {
    if (!form.name.trim()) return setErrors({ name: 'Le nom est obligatoire.' });
    setSaving(true);
    setErrors({});
    const body = { name: form.name.trim(), nameAr: form.nameAr.trim(), parentId: form.parentId ? Number(form.parentId) : null, isActive: form.isActive };
    try {
      if (isNew) await admin.post('/categories', { ...body, position: 10000 });
      else await admin.patch(`/categories/${category.id}`, body);
      return onSaved(isNew ? `« ${body.name} » a été créée.` : `« ${body.name} » a été enregistrée.`);
    } catch (err) {
      setErrors({ form: err.message, ...(err.fields || {}) });
      return setSaving(false);
    }
  };

  const parents = tops.filter((c) => c.id !== category.id);
  const title = isNew ? (category.parentId ? 'Nouvelle sous-catégorie' : 'Nouvelle catégorie') : `Modifier « ${category.name} »`;
  return (
    <Modal open title={title} onClose={saving ? undefined : onClose}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>Annuler</Button>
          <Button loading={saving} onClick={save}>Enregistrer</Button>
        </>
      )}>
      <Field label="Nom (français)" htmlFor="cat-name" required error={fieldError(errors.name)}>
        <input id="cat-name" className="adm-input" value={form.name} maxLength={100} onChange={set('name')} />
      </Field>
      <Field label="Nom (arabe)" htmlFor="cat-name-ar" hint="Affiché sur la version arabe du site. Vide : le nom français est affiché." error={fieldError(errors.nameAr)}>
        <input id="cat-name-ar" className="adm-input" dir="rtl" lang="ar" value={form.nameAr} maxLength={100} onChange={set('nameAr')} />
      </Field>
      <Field label="Catégorie parente" htmlFor="cat-parent"
        hint={hasChildren ? 'Elle a des sous-catégories : elle reste une catégorie principale.' : 'Aucune = catégorie principale (titre de colonne dans le menu).'}
        error={fieldError(errors.parentId)}>
        <select id="cat-parent" className="adm-input" value={form.parentId ?? ''} disabled={hasChildren}
          onChange={(e) => setForm((f) => ({ ...f, parentId: e.target.value || null }))}>
          <option value="">Aucune (catégorie principale)</option>
          {parents.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </Field>
      <label className="adm-check">
        <input type="checkbox" checked={form.isActive} onChange={set('isActive')} />
        <span>Visible dans le menu de la boutique</span>
      </label>
      {errors.form && <Notice tone="danger">{errors.form}</Notice>}
    </Modal>
  );
}

const fieldError = (value) => (Array.isArray(value) ? value[0] : value);

/** Produits rattachés à la catégorie : cocher / décocher. Les autres catégories des produits ne changent pas. */
function ProductsDialog({ category, onClose, onSaved }) {
  const products = useApi('/products', { page_size: 100, ordering: 'position' });
  const linked = useApi(`/categories/${category.id}/products`);
  const [picked, setPicked] = useState(null);
  const [query, setQuery] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const selection = picked ?? new Set(linked.data?.productIds || []);
  const items = (products.data?.items || []).filter((p) => `${p.displayName} ${p.brand || ''}`.toLowerCase().includes(query.trim().toLowerCase()));

  const toggle = (id) => {
    const next = new Set(selection);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setPicked(next);
  };
  const save = async () => {
    setSaving(true);
    setError('');
    try {
      await admin.put(`/categories/${category.id}/products`, { productIds: [...selection] });
      onSaved(`Produits de « ${category.name} » enregistrés (${selection.size}).`);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  const loading = !products.data || !linked.data;
  return (
    <Modal open size="lg" title={`Produits de « ${category.name} »`} onClose={saving ? undefined : onClose}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>Annuler</Button>
          <Button loading={saving} disabled={loading} onClick={save}>Enregistrer ({selection.size})</Button>
        </>
      )}>
      <p className="adm-muted">Cochez les produits à afficher dans cette catégorie. Leurs autres catégories, prix, stocks et statuts ne changent pas.</p>
      <input className="adm-input" type="search" placeholder="Rechercher un produit…" aria-label="Rechercher un produit"
        value={query} onChange={(e) => setQuery(e.target.value)} />
      {(products.error || linked.error) && <ErrorState error={products.error || linked.error} onRetry={() => { products.reload(); linked.reload(); }} />}
      {loading && !products.error && !linked.error && <SkeletonRows rows={4} />}
      {!loading && (
        <ul className="adm-cat-products">
          {items.map((p) => {
            const s = PRODUCT_STATUS[p.status];
            return (
              <li key={p.id}>
                <label className="adm-check">
                  <input type="checkbox" checked={selection.has(p.id)} onChange={() => toggle(p.id)} />
                  {p.image ? <img src={p.image} alt="" width="36" height="36" /> : <span className="adm-cat-products__ph" />}
                  <span className="adm-cat-products__name">{p.displayName}</span>
                  {s && <Badge tone={s.tone}>{s.label}</Badge>}
                </label>
              </li>
            );
          })}
          {items.length === 0 && <li className="adm-muted">Aucun produit trouvé.</li>}
        </ul>
      )}
      {error && <Notice tone="danger">{error}</Notice>}
    </Modal>
  );
}
