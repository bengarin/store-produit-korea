import { useState } from 'react';
import { ArrowDown, ArrowUp, Eye, EyeOff, ImagePlus, Layers, ListChecks, Pencil, Plus, Trash2, X } from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import MediaPicker from '../components/theme/MediaPicker.jsx';
import { Badge, Button, Card, EmptyState, ErrorState, Field, Modal, Notice, PageHeader, SkeletonRows } from '../components/ui.jsx';
import { COUNTRIES, collectionRules, countryName } from '../countries.js';
import { PRODUCT_STATUS } from '../format.js';
import { useApi, useTitle } from '../hooks.js';
import { can } from '../permissions.js';

/**
 * Admin → Collections (« Soins naturels », « Beauté chinoise »…) : regroupements de produits EXISTANTS.
 * Un produit peut être dans plusieurs collections : une seule fiche, un seul stock, un seul prix.
 * - Textes FR / AR, image, ordre, visibilité, règles d'entrée : Propriétaire et Admin.
 * - Produits d'une collection : + Éditeur. Le serveur refuse un produit qui ne respecte pas les règles.
 * Une collection n'apparaît dans la boutique que si elle est visible ET contient au moins un produit en ligne.
 */
export default function CollectionsPage() {
  useTitle('Collections');
  const { user } = useAuth();
  const editable = can(user, 'manageCategories');
  const canAssign = can(user, 'editProducts');
  const { data, error, reload, setData } = useApi('/collections');
  const [editing, setEditing] = useState(null); // { item? }
  const [assigning, setAssigning] = useState(null);
  const [removing, setRemoving] = useState(null);
  const [message, setMessage] = useState(null);

  const run = async (fn, ok) => {
    setMessage(null);
    try {
      await fn();
      if (ok) setMessage({ tone: 'success', text: ok });
    } catch (err) {
      setMessage({ tone: 'danger', text: err.message });
    }
    reload();
  };
  const move = (i, d) => {
    const list = [...data];
    [list[i], list[i + d]] = [list[i + d], list[i]];
    setData(list);
    run(() => admin.post('/collections/reorder', { ids: list.map((c) => c.id) }), 'Ordre des collections enregistré.');
  };
  const toggle = (c) => run(
    () => admin.patch(`/collections/${c.id}`, { isActive: !c.isActive }),
    c.isActive ? `« ${c.name} » est masquée dans la boutique.` : `« ${c.name} » est de nouveau visible.`,
  );

  return (
    <div className="adm-page">
      <PageHeader title="Collections"
        subtitle="Regroupez vos produits par univers. Un produit peut appartenir à plusieurs collections sans être dupliqué (une seule fiche, un seul stock)."
        actions={editable && <Button icon={Plus} onClick={() => setEditing({})}>Nouvelle collection</Button>} />
      {message && <Notice tone={message.tone}>{message.text}</Notice>}
      {error && <ErrorState error={error} onRetry={reload} />}
      {!data && !error && <Card><SkeletonRows /></Card>}
      {data && data.length === 0 && (
        <Card><EmptyState icon={Layers} title="Aucune collection" action={editable && <Button icon={Plus} onClick={() => setEditing({})}>Nouvelle collection</Button>} /></Card>
      )}
      {data && data.length > 0 && (
        <ul className="adm-colls">
          {data.map((c, i) => {
            const rules = collectionRules(c);
            const shown = c.isActive && c.activeCount > 0;
            return (
              <li key={c.id} className={`adm-coll ${c.isActive ? '' : 'is-hidden'}`}>
                <div className="adm-coll__thumb">{c.image ? <img src={c.image.src} alt="" /> : <Layers size={22} aria-hidden="true" />}</div>
                <div className="adm-coll__main">
                  <p className="adm-coll__title">
                    <strong>{c.name}</strong>
                    {c.nameAr ? <span dir="rtl" lang="ar" className="adm-cat__ar">{c.nameAr}</span> : <span className="adm-cat__ar is-missing">Nom arabe à saisir</span>}
                    {shown ? <Badge tone="success">Visible dans la boutique</Badge> : <Badge tone="muted">{c.isActive ? 'Pas encore affichée' : 'Masquée'}</Badge>}
                  </p>
                  {c.description && <p className="adm-coll__desc">{c.description}</p>}
                  <p className="adm-muted adm-coll__meta">
                    {c.productCount} produit{c.productCount > 1 ? 's' : ''} ({c.activeCount} en ligne)
                    {rules.length > 0 && <> · Règles : {rules.join(' · ')}</>}
                  </p>
                  {c.isActive && c.activeCount === 0 && (
                    <p className="adm-coll__hint">Ajoutez au moins un produit en ligne pour l’afficher dans le menu « Boutique » et sur l’accueil.</p>
                  )}
                  <div className="adm-coll__actions">
                    {canAssign && <Button variant="secondary" size="sm" icon={ListChecks} onClick={() => setAssigning(c)}>Produits</Button>}
                    {editable && (
                      <>
                        <Button variant="ghost" size="sm" icon={Pencil} onClick={() => setEditing({ item: c })}>Modifier</Button>
                        <Button variant="ghost" size="sm" icon={c.isActive ? EyeOff : Eye} onClick={() => toggle(c)}>{c.isActive ? 'Masquer' : 'Afficher'}</Button>
                        <Button variant="ghost" size="sm" icon={ArrowUp} aria-label={`Monter « ${c.name} »`} disabled={i === 0} onClick={() => move(i, -1)} />
                        <Button variant="ghost" size="sm" icon={ArrowDown} aria-label={`Descendre « ${c.name} »`} disabled={i === data.length - 1} onClick={() => move(i, 1)} />
                        <Button variant="ghost" size="sm" icon={Trash2} aria-label={`Supprimer « ${c.name} »`} onClick={() => setRemoving(c)} />
                      </>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      {editing && (
        <CollectionDialog item={editing.item} onClose={() => setEditing(null)}
          onSaved={(text) => { setEditing(null); setMessage({ tone: 'success', text }); reload(); }} />
      )}
      {assigning && (
        <ProductsDialog collection={assigning} onClose={() => setAssigning(null)}
          onSaved={(text) => { setAssigning(null); setMessage({ tone: 'success', text }); reload(); }} />
      )}
      {removing && (
        <ConfirmDialog danger confirmLabel="Supprimer" title="Supprimer la collection ?" onClose={() => setRemoving(null)}
          onConfirm={async () => {
            await admin.del(`/collections/${removing.id}`);
            setMessage({ tone: 'success', text: `« ${removing.name} » a été supprimée.` });
            setRemoving(null);
            reload();
          }}>
          <p>« {removing.name} » sera supprimée. Ses {removing.productCount} produit(s) restent intacts (fiche, prix, stock) : seul leur lien avec cette collection est retiré.</p>
          <p className="adm-muted">Pour la cacher temporairement, utilisez plutôt « Masquer ».</p>
        </ConfirmDialog>
      )}
    </div>
  );
}

function CollectionDialog({ item, onClose, onSaved }) {
  const [form, setForm] = useState({
    name: item?.name || '', nameAr: item?.nameAr || '', description: item?.description || '', descriptionAr: item?.descriptionAr || '',
    imageId: item?.image?.id ?? null, imageAlt: item?.imageAlt || '', isActive: item?.isActive ?? true,
    requiredOrigin: item?.requiredOrigin || '', requireIngredients: item?.requireIngredients ?? false,
  });
  const [image, setImage] = useState(item?.image || null);
  const [picking, setPicking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));
  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      if (item) await admin.patch(`/collections/${item.id}`, form);
      else await admin.post('/collections', form);
      onSaved(item ? `« ${form.name} » enregistrée.` : `« ${form.name} » créée.`);
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  };
  const fieldError = (k) => error?.fieldMessage?.(k);
  return (
    <Modal open size="lg" title={item ? `Modifier « ${item.name} »` : 'Nouvelle collection'} onClose={busy ? undefined : onClose}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Annuler</Button>
          <Button loading={busy} onClick={save}>Enregistrer</Button>
        </>
      )}>
      {error && !error.fields && <Notice tone="danger">{error.message}</Notice>}
      <div className="adm-grid-2">
        <Field label="Nom (français)" htmlFor="col-name" required error={fieldError('name')}>
          <input id="col-name" className="adm-input" maxLength={80} value={form.name} onChange={set('name')} autoFocus />
        </Field>
        <Field label="Nom (arabe)" htmlFor="col-name-ar" hint="Vide : le nom français s’affiche." error={fieldError('nameAr')}>
          <input id="col-name-ar" className="adm-input" dir="rtl" lang="ar" maxLength={80} value={form.nameAr} onChange={set('nameAr')} />
        </Field>
        <Field label="Description (français)" htmlFor="col-desc" hint="Courte : carte de l’accueil, menu et page de la collection (300 caractères max.)." error={fieldError('description')}>
          <textarea id="col-desc" className="adm-input" rows={3} maxLength={300} value={form.description} onChange={set('description')} />
        </Field>
        <Field label="Description (arabe)" htmlFor="col-desc-ar" error={fieldError('descriptionAr')}>
          <textarea id="col-desc-ar" className="adm-input" dir="rtl" lang="ar" rows={3} maxLength={300} value={form.descriptionAr} onChange={set('descriptionAr')} />
        </Field>
      </div>
      <div className="adm-coll-image">
        <div className="adm-coll__thumb adm-coll__thumb--lg">{image ? <img src={image.src} alt="" /> : <Layers size={26} aria-hidden="true" />}</div>
        <div className="adm-coll-image__side">
          <p className="adm-field__label">Image</p>
          <p className="adm-muted">Sans image : la photo du premier produit de la collection est utilisée.</p>
          <div className="adm-coll__actions">
            <Button variant="secondary" size="sm" icon={ImagePlus} onClick={() => setPicking(true)}>{image ? 'Changer l’image' : 'Choisir une image'}</Button>
            {image && <Button variant="ghost" size="sm" icon={X} onClick={() => { setImage(null); setForm((f) => ({ ...f, imageId: null })); }}>Retirer</Button>}
          </div>
          <Field label="Texte alternatif" htmlFor="col-alt" error={fieldError('imageAlt')}>
            <input id="col-alt" className="adm-input" maxLength={255} value={form.imageAlt} onChange={set('imageAlt')} />
          </Field>
        </div>
      </div>
      <fieldset className="adm-coll-rules">
        <legend className="adm-field__label">Règles d’entrée (vérifiées pour chaque produit)</legend>
        <p className="adm-muted">Elles évitent d’affirmer une origine ou un caractère « naturel » sans information vérifiée sur la fiche produit.</p>
        <Field label="Pays de fabrication exigé" htmlFor="col-origin" error={fieldError('requiredOrigin')}>
          <select id="col-origin" className="adm-input" value={form.requiredOrigin} onChange={set('requiredOrigin')}>
            <option value="">Aucun</option>
            {COUNTRIES.map(([code, name]) => <option key={code} value={code}>{name}</option>)}
          </select>
        </Field>
        <label className="adm-check">
          <input type="checkbox" checked={form.requireIngredients} onChange={set('requireIngredients')} />
          <span>Liste d’ingrédients obligatoire sur la fiche produit</span>
        </label>
      </fieldset>
      <label className="adm-check">
        <input type="checkbox" checked={form.isActive} onChange={set('isActive')} />
        <span>Visible dans la boutique (dès qu’un produit en ligne y est rangé)</span>
      </label>
      {picking && (
        <MediaPicker canUpload onClose={() => setPicking(false)}
          onPick={(m) => {
            setImage({ id: m.id, src: m.url640 || m.url, alt: m.alt });
            setForm((f) => ({ ...f, imageId: m.id, imageAlt: f.imageAlt || m.alt || '' }));
            setPicking(false);
          }} />
      )}
    </Modal>
  );
}

function ProductsDialog({ collection, onClose, onSaved }) {
  const { data, error } = useApi(`/collections/${collection.id}/products`);
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const chosen = selected ?? data?.productIds ?? [];
  const toggle = (id) => setSelected(chosen.includes(id) ? chosen.filter((x) => x !== id) : [...chosen, id]);
  const save = async () => {
    setBusy(true);
    setSaveError(null);
    try {
      await admin.put(`/collections/${collection.id}/products`, { productIds: chosen });
      onSaved(`Produits de « ${collection.name} » enregistrés.`);
    } catch (e) {
      setSaveError(e);
      setBusy(false);
    }
  };
  const rules = collectionRules(collection);
  const problems = saveError?.fields?.productIds;
  return (
    <Modal open size="lg" title={`Produits de « ${collection.name} »`} onClose={busy ? undefined : onClose}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Annuler</Button>
          <Button loading={busy} onClick={save} disabled={!data}>Enregistrer</Button>
        </>
      )}>
      <p className="adm-muted">
        Cochez les produits de la collection. Ils gardent leur fiche, leur prix et leur stock.
        {rules.length > 0 && <> Règles : {rules.join(' · ')}.</>}
      </p>
      {error && <ErrorState error={error} />}
      {saveError && <Notice tone="danger">{Array.isArray(problems) ? problems.join(' ') : saveError.message}</Notice>}
      {!data && !error && <SkeletonRows rows={4} />}
      {data && (
        <ul className="adm-coll-products">
          {data.products.map((p) => {
            const checked = chosen.includes(p.id);
            const status = PRODUCT_STATUS[p.status];
            return (
              <li key={p.id}>
                <label className={`adm-check ${!p.eligible && checked ? 'has-error' : ''}`}>
                  <input type="checkbox" checked={checked} disabled={!p.eligible && !checked} onChange={() => toggle(p.id)} />
                  <span>
                    <strong>{p.name}</strong> {status && <Badge tone={status.tone}>{status.label}</Badge>}
                    <span className="adm-coll-products__meta">
                      Pays de fabrication : {p.originCountry ? countryName(p.originCountry) : 'non renseigné'}
                      {' · '}Ingrédients : {p.hasIngredients ? 'renseignés' : 'non renseignés'}
                    </span>
                    {!p.eligible && <span className="adm-collection-option__why">Non disponible : {p.reasons.map((r) => r.replace(/^« [^»]+ » : /, '')).join(' ')} Complétez la fiche produit d’abord.</span>}
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      )}
    </Modal>
  );
}
