import { useRef, useState } from 'react';
import { ArrowDown, ArrowUp, Eye, EyeOff, ImagePlus, Plus, RefreshCw, Save, Trash2, X } from 'lucide-react';
import { admin } from '../api.js';
import { useToast } from '../../context/ToastContext.jsx';
import ConfirmDialog from './ConfirmDialog.jsx';
import { Badge, Button, ButtonLink, Card, EmptyState, ErrorState, Field, Notice, SkeletonRows } from './ui.jsx';
import { useApi } from '../hooks.js';
import { ASSETS } from '../../theme/assets.js';

const ACCEPT = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_MB = 10;
const TEXTS = [
  ['eyebrow', 'Sur-titre (facultatif)', 80],
  ['title', 'Titre', 120],
  ['text', 'Description (facultative)', 300],
  ['buttonLabel', 'Texte du bouton (facultatif)', 40],
  ['alt', 'Description de l’image (accessibilité)', 255],
];
const FIELDS = [...TEXTS.flatMap(([k]) => [`${k}Fr`, `${k}Ar`]), 'buttonLink'];
const EMPTY = Object.fromEntries(FIELDS.map((k) => [k, '']));

async function uploadMedia(file, alt) {
  if (!ACCEPT.includes(file.type)) throw new Error('Format refusé (JPEG, PNG ou WebP).');
  if (file.size > MAX_MB * 1024 * 1024) throw new Error(`Fichier trop lourd (${MAX_MB} Mo max.).`);
  const data = new FormData();
  data.append('file', file);
  data.append('alt', alt || '');
  return admin.upload('/media', data);
}

/** Aperçu d'une image de diapositive : média de la médiathèque ou visuel intégré au site. */
function preview(media, asset) {
  if (media) return { src: media.url640 || media.url, width: media.width, height: media.height };
  const a = asset && ASSETS[asset];
  return a ? { src: a.src, width: a.width, height: a.height } : null;
}

function firstError(err, keys) {
  for (const k of keys) {
    const m = err.fieldMessage?.(k);
    if (m) return m;
  }
  return err.message;
}

/** Choix d'une image (téléversée dans la médiathèque dès qu'elle est choisie). */
function ImagePick({ label, hint, image, onPick, onRemove, disabled, busy }) {
  const ref = useRef(null);
  return (
    <div className="adm-hero-img">
      <p className="adm-hero-img__label">{label}</p>
      <div className={`adm-hero-img__box ${image ? '' : 'is-empty'}`}>
        {image ? <img src={image.src} alt="" width={image.width} height={image.height} loading="lazy" /> : <span>{hint}</span>}
      </div>
      {!disabled && (
        <div className="adm-hero-img__actions">
          <Button size="sm" variant="secondary" icon={image ? RefreshCw : ImagePlus} loading={busy} onClick={() => ref.current?.click()}>
            {image ? 'Remplacer' : 'Choisir une image'}
          </Button>
          {image && onRemove && <Button size="sm" variant="ghost" icon={X} onClick={onRemove}>Retirer</Button>}
          <input ref={ref} type="file" accept={ACCEPT.join(',')} hidden aria-label={label}
            onChange={(e) => { if (e.target.files[0]) onPick(e.target.files[0]); e.target.value = ''; }} />
        </div>
      )}
    </div>
  );
}

/**
 * Formulaire d'une diapositive (création ou modification). Les textes FR et AR sont posés sur l'image par la
 * boutique (jamais incrustés). Arabe vide = la boutique arabe affiche la traduction existante du français.
 */
function SlideForm({ slide, index, total, editable, canDelete, onSaved, onCreated, onCancel, onMove, onDelete, toast }) {
  const isNew = !slide;
  const initial = isNew ? { ...EMPTY, isActive: false } : slide;
  const [form, setForm] = useState(initial);
  const [images, setImages] = useState(() => ({
    desktop: isNew ? null : { media: slide.desktop, asset: slide.desktopAsset },
    mobile: isNew ? null : { media: slide.mobile, asset: slide.mobileAsset },
  }));
  const [imgChange, setImgChange] = useState({}); // { desktop: {mediaId}|..., mobile: {mediaId}|null }
  const [uploading, setUploading] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const uid = isNew ? 'new' : slide.id;
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const dirty = FIELDS.some((k) => form[k] !== initial[k]) || Object.keys(imgChange).length > 0;

  const pick = (side) => async (file) => {
    setUploading(side);
    setError('');
    try {
      const media = await uploadMedia(file, form.altFr || form.titleFr);
      setImages((im) => ({ ...im, [side]: { media: { id: media.id, url: media.url, url640: media.url640, width: media.width, height: media.height } } }));
      setImgChange((c) => ({ ...c, [side]: media.id }));
    } catch (err) {
      setError(firstError(err, ['file']));
    } finally {
      setUploading('');
    }
  };
  const removeMobile = () => {
    setImages((im) => ({ ...im, mobile: null }));
    setImgChange((c) => ({ ...c, mobile: null }));
  };

  const body = () => {
    const out = Object.fromEntries(FIELDS.filter((k) => isNew || form[k] !== initial[k]).map((k) => [k, form[k]]));
    if ('desktop' in imgChange) out.desktopMediaId = imgChange.desktop;
    if ('mobile' in imgChange) {
      out.mobileMediaId = imgChange.mobile;
      if (imgChange.mobile === null) out.mobileAsset = '';
    }
    return out;
  };

  const save = async (extra = {}) => {
    setSaving(true);
    setError('');
    try {
      if (isNew) {
        const created = await admin.post('/hero-slides', { ...body(), isActive: Boolean(extra.isActive) });
        toast(extra.isActive ? 'Diapositive créée et publiée' : 'Diapositive créée (non publiée)');
        onCreated(created);
      } else {
        const saved = await admin.patch(`/hero-slides/${slide.id}`, { ...body(), ...extra });
        setImgChange({});
        setForm(saved);
        onSaved(saved);
        toast('isActive' in extra ? (extra.isActive ? 'Diapositive publiée' : 'Diapositive dépubliée') : 'Diapositive enregistrée');
      }
    } catch (err) {
      setError(firstError(err, ['titleFr', 'desktopMediaId', 'buttonLink', ...FIELDS, 'mobileMediaId']));
    } finally {
      setSaving(false);
    }
  };

  const desktop = images.desktop && preview(images.desktop.media, images.desktop.asset);
  const mobile = images.mobile && preview(images.mobile.media, images.mobile.asset);
  const published = !isNew && slide.isActive;

  return (
    <li className={`adm-hero-slide ${isNew || published ? '' : 'is-hidden'}`}>
      <header className="adm-hero-slide__head">
        <strong>{isNew ? 'Nouvelle diapositive' : `Diapositive ${index + 1}`}</strong>
        {!isNew && <Badge tone={published ? 'success' : 'neutral'}>{published ? 'Publiée' : 'Non publiée'}</Badge>}
        {!isNew && editable && (
          <span className="adm-hero-slide__order">
            <Button size="sm" variant="ghost" icon={ArrowUp} disabled={index === 0} onClick={() => onMove(-1)} aria-label={`Monter la diapositive ${index + 1}`} />
            <Button size="sm" variant="ghost" icon={ArrowDown} disabled={index === total - 1} onClick={() => onMove(1)} aria-label={`Descendre la diapositive ${index + 1}`} />
          </span>
        )}
      </header>

      <div className="adm-hero-slide__images">
        <ImagePick label="Image ordinateur *" hint="Paysage, idéalement 1672 × 800 px" image={desktop}
          onPick={pick('desktop')} disabled={!editable} busy={uploading === 'desktop'} />
        <ImagePick label="Image mobile (facultative)" hint="Portrait, idéalement 941 × 1388 px. Sans image mobile : l’image ordinateur est utilisée."
          image={mobile} onPick={pick('mobile')} onRemove={removeMobile} disabled={!editable} busy={uploading === 'mobile'} />
      </div>

      <div className="adm-hero-slide__langs">
        {[['Fr', 'Français', undefined], ['Ar', 'Arabe', 'rtl']].map(([suffix, label, dir]) => (
          <fieldset key={suffix} className="adm-hero-slide__lang">
            <legend>{label}{suffix === 'Ar' && <small> — vide = traduction automatique du texte français</small>}</legend>
            {TEXTS.map(([key, fieldLabel, max]) => {
              const id = `hs-${uid}-${key}${suffix}`;
              const Tag = key === 'text' ? 'textarea' : 'input';
              return (
                <Field key={key} label={fieldLabel} htmlFor={id} required={key === 'title' && suffix === 'Fr'}>
                  <Tag id={id} className="adm-input" maxLength={max} value={form[`${key}${suffix}`] || ''} onChange={set(`${key}${suffix}`)}
                    disabled={!editable} dir={dir} rows={key === 'text' ? 2 : undefined} />
                </Field>
              );
            })}
          </fieldset>
        ))}
      </div>

      <Field label="Destination du bouton" htmlFor={`hs-${uid}-link`}
        hint="Page de la boutique (/produits, /collections/…), ancre de l’accueil (#collection) ou adresse https://. Le bouton ne s’affiche qu’avec un texte et une destination.">
        <input id={`hs-${uid}-link`} className="adm-input" maxLength={300} value={form.buttonLink || ''} onChange={set('buttonLink')} disabled={!editable} dir="ltr" placeholder="/produits" />
      </Field>

      {error && <Notice tone="danger">{error}</Notice>}

      {editable && (
        <div className="adm-hero-slide__actions">
          {isNew ? (
            <>
              <Button icon={Eye} loading={saving} onClick={() => save({ isActive: true })}>Créer et publier</Button>
              <Button variant="secondary" icon={Save} loading={saving} onClick={() => save()}>Créer sans publier</Button>
              <Button variant="ghost" onClick={onCancel}>Annuler</Button>
            </>
          ) : (
            <>
              {dirty && <Button icon={Save} loading={saving} onClick={() => save()}>Enregistrer</Button>}
              <Button variant="secondary" icon={published ? EyeOff : Eye} loading={saving} onClick={() => save({ isActive: !published })}>
                {published ? 'Dépublier' : 'Publier'}
              </Button>
              {canDelete && <Button variant="danger" icon={Trash2} onClick={onDelete}>Supprimer</Button>}
            </>
          )}
        </div>
      )}
    </li>
  );
}

/** Admin → Visuels marketing → Bannière d'accueil : diapositives (ajout, modification, ordre, publication, suppression). */
export default function HeroSlidesManager({ editable, canDelete }) {
  const toast = useToast();
  const { data, error, reload, setData } = useApi('/hero-slides');
  const [adding, setAdding] = useState(false);
  const [toDelete, setToDelete] = useState(null);

  if (error) return <Card><ErrorState error={error} onRetry={reload} /></Card>;
  if (!data) return <Card><SkeletonRows rows={3} /></Card>;
  const items = data.items;
  const live = items.filter((s) => s.isActive).length;
  const replace = (saved) => setData({ ...data, items: items.map((s) => (s.id === saved.id ? saved : s)) });

  const move = async (index, delta) => {
    const ordered = [...items];
    [ordered[index], ordered[index + delta]] = [ordered[index + delta], ordered[index]];
    setData({ ...data, items: ordered });
    try {
      await admin.post('/hero-slides/reorder', { ids: ordered.map((s) => s.id) });
      toast('Ordre enregistré');
    } catch (err) {
      toast(err.message, 'info');
      reload();
    }
  };
  const remove = async () => {
    await admin.del(`/hero-slides/${toDelete.id}`);
    toast('Diapositive supprimée (les images restent dans la médiathèque)');
    setToDelete(null);
    reload();
  };

  return (
    <>
      <Card
        title="Bannière de l’accueil"
        actions={<ButtonLink href="/" target="_blank" rel="noopener noreferrer" icon={Eye}>Voir l’accueil</ButtonLink>}
      >
        <p className="adm-muted">
          Une diapositive publiée = bannière fixe. Plusieurs = carrousel (défilement automatique, flèches, points, glissement sur mobile).
          Les textes s’affichent par-dessus l’image, à gauche sur ordinateur et en haut sur mobile : choisissez des images sans texte, avec cette zone dégagée. Les modifications sont visibles tout de suite sur la boutique.
        </p>
        <p className="adm-hero-summary">
          <strong>{live}</strong> publiée{live > 1 ? 's' : ''} sur {items.length} — {live === 0 ? 'aucune bannière affichée' : live === 1 ? 'bannière fixe' : 'carrousel'}
        </p>
        {live === 0 && <Notice tone="warning">Aucune diapositive publiée : l’accueil s’affiche sans bannière principale.</Notice>}
      </Card>

      {items.length === 0 && !adding && (
        <Card><EmptyState icon={ImagePlus} title="Aucune diapositive" text="Ajoutez une diapositive pour afficher une bannière sur l’accueil." /></Card>
      )}

      <ul className="adm-hero-list">
        {items.map((slide, i) => (
          <SlideForm key={`${slide.id}-${slide.desktopMediaId}-${slide.mobileMediaId}-${slide.mobileAsset}`} slide={slide} index={i} total={items.length}
            editable={editable} canDelete={canDelete} toast={toast} onSaved={replace} onMove={(d) => move(i, d)} onDelete={() => setToDelete(slide)} />
        ))}
        {adding && (
          <SlideForm editable toast={toast} onCancel={() => setAdding(false)}
            onCreated={() => { setAdding(false); reload(); }} />
        )}
      </ul>

      {editable && !adding && (
        <div><Button icon={Plus} onClick={() => setAdding(true)}>Ajouter une diapositive</Button></div>
      )}

      {toDelete && (
        <ConfirmDialog title="Supprimer cette diapositive ?" confirmLabel="Supprimer" danger onConfirm={remove} onClose={() => setToDelete(null)}>
          « {toDelete.titleFr} » est retirée de l’accueil. Les images restent dans la médiathèque. Pour la masquer sans la perdre, utilisez plutôt « Dépublier ».
        </ConfirmDialog>
      )}
    </>
  );
}
