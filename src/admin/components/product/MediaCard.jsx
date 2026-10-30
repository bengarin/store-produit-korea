import { useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, ImagePlus, Settings2, Star, Trash2, Upload } from 'lucide-react';
import { admin } from '../../api.js';
import ConfirmDialog from '../ConfirmDialog.jsx';
import { Badge, Button, Card, Field, Modal, Notice } from '../ui.jsx';

const ACCEPT = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_MB = 10;
const KINDS = [
  ['packshot', 'Packshot'], ['texture', 'Texture'], ['in-use', 'Application'], ['in-hand', 'En main'],
  ['lifestyle', 'Ambiance'], ['ingredient', 'Ingrédient'], ['packaging', 'Emballage'], ['scene', 'En situation'], ['other', 'Autre'],
];

function ImageSettings({ image, onClose, onSaved }) {
  const [form, setForm] = useState({ alt: image.alt, fit: image.fit, kind: image.kind, focalPosition: image.focalPosition || '', inGallery: image.inGallery });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      onSaved(await admin.patch(`/product-images/${image.id}`, form));
    } catch (err) {
      setErrors({ focalPosition: err.fieldMessage('focalPosition'), form: err.fieldMessage('focalPosition') ? null : err.message });
      setBusy(false);
    }
  };
  return (
    <Modal open title="Réglages de l’image" onClose={onClose}
      footer={<><Button variant="secondary" onClick={onClose}>Annuler</Button><Button type="submit" form="adm-img-form" loading={busy}>Enregistrer</Button></>}>
      <form id="adm-img-form" onSubmit={save} noValidate>
        <img src={image.url640 || image.url} alt="" className={`adm-img-preview adm-img-preview--${form.fit}`} style={form.focalPosition ? { objectPosition: form.focalPosition } : undefined} />
        <Field label="Texte alternatif (décrit l’image pour l’accessibilité et le référencement)" htmlFor="img-alt">
          <input id="img-alt" className="adm-input" maxLength={255} value={form.alt} onChange={(e) => setForm((f) => ({ ...f, alt: e.target.value }))} />
        </Field>
        <div className="adm-form-grid adm-mt">
          <Field label="Affichage" htmlFor="img-fit">
            <select id="img-fit" className="adm-input" value={form.fit} onChange={(e) => setForm((f) => ({ ...f, fit: e.target.value }))}>
              <option value="contain">Packshot entier (fond crème)</option>
              <option value="cover">Photo d’ambiance (remplit le cadre)</option>
            </select>
          </Field>
          <Field label="Type de photo" htmlFor="img-kind">
            <select id="img-kind" className="adm-input" value={form.kind} onChange={(e) => setForm((f) => ({ ...f, kind: e.target.value }))}>
              {KINDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </Field>
          <Field label="Cadrage (facultatif)" htmlFor="img-focal" error={errors.focalPosition} hint="Ex. « 50% 30% » : horizontal puis vertical.">
            <input id="img-focal" className="adm-input" value={form.focalPosition} onChange={(e) => setForm((f) => ({ ...f, focalPosition: e.target.value }))} />
          </Field>
          <label className="adm-check">
            <input type="checkbox" checked={form.inGallery} onChange={(e) => setForm((f) => ({ ...f, inGallery: e.target.checked }))} />
            Afficher dans la galerie de la fiche
          </label>
        </div>
        {errors.form && <Notice tone="danger">{errors.form}</Notice>}
      </form>
    </Modal>
  );
}

/**
 * Images du produit. La 1re image de la galerie est l'image principale (cartes, panier, fiche).
 * Envoi : POST /media (fichier vérifié et ré-encodé par le serveur) puis rattachement au produit.
 */
export default function MediaCard({ product, editable, onChanged, toast }) {
  const inputRef = useRef(null);
  const [uploads, setUploads] = useState([]); // { name, status, message }
  const [dragOver, setDragOver] = useState(false);
  const [dragId, setDragId] = useState(null);
  const [settings, setSettings] = useState(null);
  const [toDelete, setToDelete] = useState(null);
  const gallery = product.images.filter((i) => i.inGallery).sort((a, b) => a.position - b.position);
  const others = product.images.filter((i) => !i.inGallery);

  const uploadFiles = async (files) => {
    const list = [...files];
    setUploads(list.map((f) => ({ name: f.name, status: 'pending' })));
    let position = gallery.length;
    for (const [i, file] of list.entries()) {
      const update = (patch) => setUploads((u) => u.map((x, j) => (j === i ? { ...x, ...patch } : x)));
      if (!ACCEPT.includes(file.type)) { update({ status: 'error', message: 'Format refusé (JPEG, PNG ou WebP).' }); continue; }
      if (file.size > MAX_MB * 1024 * 1024) { update({ status: 'error', message: `Fichier trop lourd (${MAX_MB} Mo max.).` }); continue; }
      try {
        const data = new FormData();
        data.append('file', file);
        data.append('alt', product.displayName || product.name);
        const media = await admin.upload('/media', data);
        await admin.post(`/products/${product.id}/images`, {
          mediaId: media.id, alt: product.displayName || product.name, fit: 'contain',
          kind: position === 0 ? 'packshot' : 'other',
        });
        position += 1;
        update({ status: 'done' });
      } catch (err) {
        update({ status: 'error', message: err.fieldMessage('file') || err.fieldMessage('mediaId') || err.message });
      }
    }
    onChanged();
  };

  const reorder = async (ids) => {
    try {
      await admin.post(`/products/${product.id}/images/reorder`, { ids });
      onChanged();
    } catch (err) {
      toast(err.message, 'info');
    }
  };
  const move = (id, to) => {
    const ids = gallery.map((g) => g.id).filter((x) => x !== id);
    ids.splice(Math.max(0, Math.min(to, ids.length)), 0, id);
    reorder(ids);
  };

  return (
    <Card title="Images" actions={editable && (
      <Button size="sm" variant="secondary" icon={ImagePlus} onClick={() => inputRef.current?.click()}>Ajouter des images</Button>
    )}>
      {editable && (
        <div
          className={`adm-dropzone ${dragOver ? 'is-over' : ''}`}
          onDragOver={(e) => { if (e.dataTransfer.types.includes('Files')) { e.preventDefault(); setDragOver(true); } }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { if (e.dataTransfer.files.length) { e.preventDefault(); setDragOver(false); uploadFiles(e.dataTransfer.files); } }}
        >
          <Upload size={20} aria-hidden="true" />
          <p><button type="button" className="adm-link-btn" onClick={() => inputRef.current?.click()}>Choisissez des images</button> ou déposez-les ici</p>
          <p className="adm-muted">JPEG, PNG ou WebP · {MAX_MB} Mo max. · converties en WebP, métadonnées supprimées</p>
          <input ref={inputRef} type="file" accept={ACCEPT.join(',')} multiple hidden aria-label="Ajouter des images"
            onChange={(e) => { if (e.target.files.length) uploadFiles(e.target.files); e.target.value = ''; }} />
        </div>
      )}
      {uploads.length > 0 && (
        <ul className="adm-uploads" aria-live="polite">
          {uploads.map((u, i) => (
            <li key={`${u.name}-${i}`}>
              <span>{u.name}</span>
              {u.status === 'pending' && <Badge>Envoi…</Badge>}
              {u.status === 'done' && <Badge tone="success">Ajoutée</Badge>}
              {u.status === 'error' && <span className="adm-field__error">{u.message}</span>}
            </li>
          ))}
        </ul>
      )}

      {gallery.length === 0 ? (
        <Notice tone="warning">Aucune image dans la galerie : une image est obligatoire pour activer le produit.</Notice>
      ) : (
        <ol className="adm-gallery" aria-label="Galerie (glisser pour réordonner)">
          {gallery.map((img, index) => (
            <li
              key={img.id}
              className={`adm-gallery__item ${index === 0 ? 'is-main' : ''} ${dragId === img.id ? 'is-dragging' : ''}`}
              draggable={editable}
              onDragStart={(e) => { setDragId(img.id); e.dataTransfer.effectAllowed = 'move'; }}
              onDragEnd={() => setDragId(null)}
              onDragOver={(e) => { if (dragId) e.preventDefault(); }}
              onDrop={(e) => { e.preventDefault(); if (dragId && dragId !== img.id) move(dragId, index); setDragId(null); }}
            >
              <img src={img.url640 || img.url} alt={img.alt} className={`adm-gallery__img adm-gallery__img--${img.fit}`} loading="lazy" />
              {index === 0 && <span className="adm-gallery__main"><Star size={12} aria-hidden="true" /> Principale</span>}
              {editable && (
                <div className="adm-gallery__tools">
                  <button type="button" aria-label={`Déplacer à gauche : ${img.alt || `image ${index + 1}`}`} disabled={index === 0} onClick={() => move(img.id, index - 1)}><ArrowLeft size={15} /></button>
                  <button type="button" aria-label={`Déplacer à droite : ${img.alt || `image ${index + 1}`}`} disabled={index === gallery.length - 1} onClick={() => move(img.id, index + 1)}><ArrowRight size={15} /></button>
                  {index > 0 && <button type="button" aria-label="Définir comme image principale" title="Définir comme principale" onClick={() => move(img.id, 0)}><Star size={15} /></button>}
                  <button type="button" aria-label="Réglages de l’image" title="Réglages" onClick={() => setSettings(img)}><Settings2 size={15} /></button>
                  <button type="button" aria-label="Supprimer l’image" title="Supprimer" className="is-danger" onClick={() => setToDelete(img)}><Trash2 size={15} /></button>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
      {others.length > 0 && (
        <>
          <p className="adm-subtitle">Hors galerie <span className="adm-muted">(ex. visuel « en situation » de l’accueil)</span></p>
          <ul className="adm-gallery adm-gallery--small">
            {others.map((img) => (
              <li key={img.id} className="adm-gallery__item">
                <img src={img.url640 || img.url} alt={img.alt} className={`adm-gallery__img adm-gallery__img--${img.fit}`} loading="lazy" />
                {editable && (
                  <div className="adm-gallery__tools">
                    <button type="button" aria-label="Réglages de l’image" onClick={() => setSettings(img)}><Settings2 size={15} /></button>
                    <button type="button" aria-label="Supprimer l’image" className="is-danger" onClick={() => setToDelete(img)}><Trash2 size={15} /></button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
      <p className="adm-footnote adm-mt">La 1re image est l’image principale (cartes, panier, haut de la fiche). Glissez les images ou utilisez les flèches pour les réordonner.</p>

      {settings && (
        <ImageSettings image={settings} onClose={() => setSettings(null)} onSaved={() => { setSettings(null); toast('Image mise à jour'); onChanged(); }} />
      )}
      {toDelete && (
        <ConfirmDialog title="Supprimer cette image ?" confirmLabel="Supprimer" danger onClose={() => setToDelete(null)}
          onConfirm={async () => {
            await admin.del(`/product-images/${toDelete.id}`);
            setToDelete(null);
            toast('Image retirée du produit');
            onChanged();
          }}>
          <img src={toDelete.url640 || toDelete.url} alt="" className="adm-img-preview adm-img-preview--small" />
          <p>L’image sera retirée de ce produit (le fichier reste dans la médiathèque). Un produit actif doit garder au moins une image.</p>
        </ConfirmDialog>
      )}
    </Card>
  );
}
