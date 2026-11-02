import { useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ArrowDown, ArrowUp, ExternalLink, ImagePlus, RefreshCw, Save, Trash2, Upload } from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import { Badge, Button, ButtonLink, Card, EmptyState, ErrorState, Field, Notice, PageHeader, SkeletonRows } from '../components/ui.jsx';
import { useApi, useTitle } from '../hooks.js';
import { can } from '../permissions.js';

const ACCEPT = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_MB = 10;
export const MARKETING_CATEGORIES = [
  ['banner', 'Bannière / présentation'],
  ['benefits', 'Bienfaits'],
  ['ingredients', 'Ingrédients clés'],
  ['usage', 'Mode d’utilisation'],
  ['before_after', 'Avant / Après'],
  ['comparison', 'Comparaison'],
  ['brand', 'La marque'],
  ['other', 'Autre'],
];
const LANGS = [
  ['fr', 'Français', 'Visuels avec du texte en français.'],
  ['ar', 'Arabe', 'Visuels avec du texte en arabe : affichés sur la boutique en arabe. Sans visuel arabe, la boutique en arabe affiche les visuels français.'],
  ['any', 'Sans texte', 'Visuels sans texte : affichés dans les deux langues.'],
];

/** Envoi d'un fichier dans la bibliothèque de médias (vérifié et converti en WebP par le serveur). */
async function uploadMedia(file, alt) {
  if (!ACCEPT.includes(file.type)) throw new Error('Format refusé (JPEG, PNG ou WebP).');
  if (file.size > MAX_MB * 1024 * 1024) throw new Error(`Fichier trop lourd (${MAX_MB} Mo max.).`);
  const data = new FormData();
  data.append('file', file);
  data.append('alt', alt);
  return admin.upload('/media', data);
}

function MarketingItem({ item, editable, canDelete, first, last, onMove, onSaved, onDelete, toast, productName }) {
  const [form, setForm] = useState(item);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const replaceRef = useRef(null);
  const fields = ['category', 'title', 'description', 'alt', 'isActive', 'authenticConfirmed'];
  const dirty = fields.some((k) => form[k] !== item[k]);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));

  const patch = async (body, message) => {
    setSaving(true);
    setError('');
    try {
      const saved = await admin.patch(`/marketing-images/${item.id}`, body);
      onSaved(saved);
      setForm(saved);
      toast(message);
    } catch (err) {
      setError(err.fieldMessage?.('authenticConfirmed') || err.fieldMessage?.('mediaId') || err.message);
    } finally {
      setSaving(false);
    }
  };
  const save = () => patch(Object.fromEntries(fields.filter((k) => form[k] !== item[k]).map((k) => [k, form[k]])), 'Visuel enregistré');
  const replace = async (file) => {
    try {
      const media = await uploadMedia(file, form.alt || productName);
      await patch({ mediaId: media.id }, 'Image remplacée');
    } catch (err) {
      setError(err.fieldMessage?.('file') || err.message);
    }
  };
  const beforeAfter = form.category === 'before_after';

  return (
    <li className={`adm-mkt-item ${item.isPublic ? '' : 'is-hidden'}`}>
      <div className="adm-mkt-item__media">
        <img src={item.url640 || item.url} alt={item.alt || ''} width={item.width} height={item.height} loading="lazy" />
        <Badge tone={item.isPublic ? 'success' : 'neutral'}>{item.isPublic ? 'Affiché' : 'Masqué'}</Badge>
      </div>
      <div className="adm-mkt-item__form">
        <div className="adm-form-grid">
          <Field label="Catégorie" htmlFor={`mk-cat-${item.id}`}>
            <select id={`mk-cat-${item.id}`} className="adm-input" value={form.category} onChange={set('category')} disabled={!editable}>
              {MARKETING_CATEGORIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </Field>
          <Field label="Titre (facultatif)" htmlFor={`mk-title-${item.id}`}>
            <input id={`mk-title-${item.id}`} className="adm-input" maxLength={120} value={form.title} onChange={set('title')} disabled={!editable}
              dir={item.language === 'ar' ? 'rtl' : undefined} />
          </Field>
          <div className="adm-form-grid__full">
            <Field label="Description (facultative)" htmlFor={`mk-desc-${item.id}`}>
              <textarea id={`mk-desc-${item.id}`} className="adm-input" rows={2} maxLength={600} value={form.description} onChange={set('description')}
                disabled={!editable} dir={item.language === 'ar' ? 'rtl' : undefined} />
            </Field>
          </div>
          <div className="adm-form-grid__full">
            <Field label="Texte alternatif (accessibilité)" htmlFor={`mk-alt-${item.id}`} hint="Décrit l’image pour les personnes malvoyantes.">
              <input id={`mk-alt-${item.id}`} className="adm-input" maxLength={255} value={form.alt} onChange={set('alt')} disabled={!editable}
                dir={item.language === 'ar' ? 'rtl' : undefined} />
            </Field>
          </div>
        </div>
        <label className="adm-check"><input type="checkbox" checked={form.isActive} onChange={set('isActive')} disabled={!editable} /> Afficher sur la fiche produit</label>
        {beforeAfter && (
          <label className="adm-check adm-mkt-item__authentic">
            <input type="checkbox" checked={form.authenticConfirmed} onChange={set('authenticConfirmed')} disabled={!editable} />
            Je confirme qu’il s’agit de photos authentiques (sans retouche, montage ni image générée)
          </label>
        )}
        {error && <Notice tone="danger">{error}</Notice>}
        {editable && (
          <div className="adm-mkt-item__actions">
            {dirty && <Button size="sm" icon={Save} loading={saving} onClick={save}>Enregistrer</Button>}
            <Button size="sm" variant="secondary" icon={ArrowUp} disabled={first} onClick={() => onMove(-1)} aria-label="Monter">Monter</Button>
            <Button size="sm" variant="secondary" icon={ArrowDown} disabled={last} onClick={() => onMove(1)} aria-label="Descendre">Descendre</Button>
            <Button size="sm" variant="secondary" icon={RefreshCw} onClick={() => replaceRef.current?.click()}>Remplacer l’image</Button>
            <input ref={replaceRef} type="file" accept={ACCEPT.join(',')} hidden aria-label="Choisir l’image de remplacement"
              onChange={(e) => { if (e.target.files[0]) replace(e.target.files[0]); e.target.value = ''; }} />
            {canDelete && <Button size="sm" variant="danger" icon={Trash2} onClick={onDelete}>Supprimer</Button>}
          </div>
        )}
      </div>
    </li>
  );
}

/** Visuels marketing d'un produit : un espace par langue (français, arabe, sans texte). */
export default function ProductMarketingPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const toast = useToast();
  const { data: product, error: productError } = useApi(`/products/${id}`);
  const { data, error, reload, setData } = useApi(`/products/${id}/marketing-images`);
  const [lang, setLang] = useState('fr');
  const [category, setCategory] = useState('banner');
  const [uploads, setUploads] = useState([]);
  const [toDelete, setToDelete] = useState(null);
  const inputRef = useRef(null);
  const editable = can(user, 'editProducts');
  const canDelete = can(user, 'deleteProducts');
  const name = product?.displayName || product?.name || '';
  useTitle(name ? `Visuels — ${name}` : 'Visuels marketing');

  if (productError || error) return <div className="adm-page"><PageHeader title="Visuels marketing" back={{ to: '/admin/marketing', label: 'Visuels marketing' }} /><ErrorState error={productError || error} onRetry={reload} /></div>;
  if (!product || !data) return <div className="adm-page"><SkeletonRows rows={6} /></div>;

  const all = data.items;
  const items = all.filter((m) => m.language === lang);
  const replaceItem = (saved) => setData({ ...data, items: all.map((m) => (m.id === saved.id ? saved : m)) });

  const uploadFiles = async (files) => {
    const list = [...files];
    setUploads(list.map((f) => ({ name: f.name, status: 'pending' })));
    for (const [i, file] of list.entries()) {
      const update = (patch) => setUploads((u) => u.map((x, j) => (j === i ? { ...x, ...patch } : x)));
      try {
        const media = await uploadMedia(file, name);
        // Avant / Après : importé masqué ; il ne s'affiche qu'après confirmation explicite d'authenticité.
        await admin.post(`/products/${id}/marketing-images`, {
          mediaId: media.id, category, language: lang, alt: name, isActive: category !== 'before_after',
        });
        update({ status: 'done' });
      } catch (err) {
        update({ status: 'error', message: err.fieldMessage?.('file') || err.message });
      }
    }
    reload();
  };

  const move = async (index, delta) => {
    const ordered = [...items];
    [ordered[index], ordered[index + delta]] = [ordered[index + delta], ordered[index]];
    // L'ordre est enregistré pour tous les visuels du produit (les autres langues gardent leur place relative).
    const others = all.filter((m) => m.language !== lang);
    const ids = [...ordered, ...others].map((m) => m.id);
    try {
      await admin.post(`/products/${id}/marketing-images/reorder`, { ids });
      reload();
    } catch (err) {
      toast(err.message, 'info');
    }
  };

  const remove = async () => {
    try {
      await admin.del(`/marketing-images/${toDelete.id}`);
      toast('Visuel supprimé (l’image reste dans la bibliothèque de médias)');
      setToDelete(null);
      reload();
    } catch (err) {
      toast(err.message, 'info');
    }
  };

  return (
    <div className="adm-page">
      <PageHeader title={`Visuels marketing — ${name}`} back={{ to: '/admin/marketing', label: 'Visuels marketing' }}
        subtitle="Affichés dans la colonne de droite de la fiche, sous les boutons de commande. Les photos du produit (galerie) se gèrent dans la fiche produit."
        actions={product.status === 'active' && <ButtonLink icon={ExternalLink} href={`/produits/${product.slug}`} target="_blank" rel="noopener noreferrer">Voir la fiche</ButtonLink>} />

      <div className="adm-tabs" role="tablist" aria-label="Langue des visuels">
        {LANGS.map(([code, label]) => {
          const n = all.filter((m) => m.language === code).length;
          return (
            <button key={code} type="button" role="tab" aria-selected={lang === code} className={`adm-tab ${lang === code ? 'is-active' : ''}`} onClick={() => setLang(code)}>
              {label} <span className="adm-tab__count">{n}</span>
            </button>
          );
        })}
      </div>
      <p className="adm-muted">{LANGS.find(([c]) => c === lang)[2]}</p>

      {editable && (
        <Card title="Importer des visuels">
          <div className="adm-mkt-upload">
            <Field label="Catégorie des images importées" htmlFor="mk-new-cat">
              <select id="mk-new-cat" className="adm-input" value={category} onChange={(e) => setCategory(e.target.value)}>
                {MARKETING_CATEGORIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </Field>
            <Button icon={Upload} onClick={() => inputRef.current?.click()}>Choisir des images ({LANGS.find(([c]) => c === lang)[1]})</Button>
            <input ref={inputRef} type="file" accept={ACCEPT.join(',')} multiple hidden aria-label="Importer des visuels marketing"
              onChange={(e) => { if (e.target.files.length) uploadFiles(e.target.files); e.target.value = ''; }} />
          </div>
          {category === 'before_after' && (
            <Notice tone="warning">Avant / Après : photos authentiques uniquement. Importées masquées : cochez la confirmation sur chaque visuel pour l’afficher.</Notice>
          )}
          {uploads.length > 0 && (
            <ul className="adm-uploads" aria-live="polite">
              {uploads.map((u, i) => <li key={i} className={`is-${u.status}`}>{u.name} — {u.status === 'pending' ? 'envoi…' : u.status === 'done' ? 'ajouté' : u.message}</li>)}
            </ul>
          )}
        </Card>
      )}

      {items.length === 0 ? (
        <Card><EmptyState icon={ImagePlus} title="Aucun visuel dans cette langue" text="Aucune section ne s’affiche sur la fiche tant qu’il n’y a pas de visuel." /></Card>
      ) : (
        <ul className="adm-mkt-list">
          {items.map((item, i) => (
            <MarketingItem key={`${item.id}-${item.mediaId}-${item.position}`} item={item} editable={editable} canDelete={canDelete} productName={name}
              first={i === 0} last={i === items.length - 1} onMove={(d) => move(i, d)} onSaved={replaceItem} toast={toast}
              onDelete={() => setToDelete(item)} />
          ))}
        </ul>
      )}

      {toDelete && (
        <ConfirmDialog title="Supprimer ce visuel ?" confirmLabel="Supprimer" danger onConfirm={remove} onClose={() => setToDelete(null)}>
          Le visuel est retiré de la fiche. L’image reste dans la bibliothèque de médias.
        </ConfirmDialog>
      )}
    </div>
  );
}
