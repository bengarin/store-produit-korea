import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Save, Undo2 } from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { HighlightsEditor, LinesField, linesToList, listToLines } from '../components/product/ContentEditors.jsx';
import MediaCard from '../components/product/MediaCard.jsx';
import PreviewModal from '../components/product/PreviewModal.jsx';
import { CategoriesCard, StatusCard } from '../components/product/SidePanels.jsx';
import VariantsCard from '../components/product/VariantsCard.jsx';
import RichTextEditor from '../components/RichTextEditor.jsx';
import { Badge, Button, Card, ErrorState, Field, Notice, PageHeader, SkeletonRows } from '../components/ui.jsx';
import { PRODUCT_STATUS } from '../format.js';
import { sanitizeRichText } from '../../utils/richText.js';
import { useApi, useTitle } from '../hooks.js';
import { can } from '../permissions.js';

/** Champs du produit enregistrés par le bouton « Enregistrer » (les images, variantes et options ont leurs propres actions). */
function toForm(p) {
  return {
    brand: p.brand, name: p.name, displayName: p.displayName, cardLine: p.cardLine, summary: p.summary,
    descriptionHtml: sanitizeRichText(p.descriptionHtml || ''), ingredients: listToLines(p.ingredients), benefits: listToLines(p.benefits),
    usage: listToLines(p.usage), skinTypes: p.skinTypes, highlights: p.highlights.map((h) => ({ ...h })),
    categoryIds: p.categories.map((c) => c.id), hoverImageId: p.hoverImageId, hoverImagePosition: p.hoverImagePosition,
    sceneImageId: p.sceneImageId, slug: p.slug, seoTitle: p.seoTitle, seoDescription: p.seoDescription, ogImageId: p.ogImageId,
  };
}
const LIST_FIELDS = ['ingredients', 'benefits', 'usage'];
const same = (a, b) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);

function Counter({ value, max }) {
  return <span className={`adm-counter ${value.length > max ? 'is-over' : ''}`}>{value.length}/{max}</span>;
}

export default function ProductEditPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const toast = useToast();
  const { data: product, error, reload, setData } = useApi(`/products/${id}`);
  const { data: categories, setData: setCategories } = useApi('/categories');
  const [form, setForm] = useState(null);
  const [version, setVersion] = useState(0); // recharge l'éditeur de texte riche après enregistrement
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState(false);
  const editable = can(user, 'editProducts');
  useTitle(product ? product.displayName || product.name : 'Produit');

  useEffect(() => {
    if (product) setForm(toForm(product));
  }, [product]);

  const initial = useMemo(() => (product ? toForm(product) : null), [product]);
  const changed = useMemo(() => (form && initial ? Object.keys(form).filter((k) => !same(form[k], initial[k])) : []), [form, initial]);
  const dirty = changed.length > 0;

  useEffect(() => {
    if (!dirty) return undefined;
    const warn = (e) => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  const refresh = useCallback(() => reload(), [reload]);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e?.target ? e.target.value : e }));

  const save = async () => {
    setSaving(true);
    setErrors({});
    const body = Object.fromEntries(changed.map((k) => {
      if (LIST_FIELDS.includes(k)) return [k, linesToList(form[k])];
      if (['hoverImageId', 'sceneImageId', 'ogImageId'].includes(k)) return [k, form[k] ? Number(form[k]) : null];
      return [k, form[k]];
    }));
    try {
      const saved = await admin.patch(`/products/${product.id}`, body);
      setData(saved);
      setVersion((n) => n + 1);
      toast('Produit enregistré');
    } catch (err) {
      const fields = err.fields || {};
      setErrors(Object.fromEntries(Object.entries(fields).map(([k, v]) => [k, Array.isArray(v) ? (typeof v[0] === 'string' ? v[0] : 'Valeur invalide') : String(v)])));
      toast(fields.status ? `Refusé : ${fields.status[0]}` : 'Certaines informations sont invalides.', 'info');
    } finally {
      setSaving(false);
    }
  };

  if (error) return <div className="adm-page"><PageHeader title="Produit" back={{ to: '/admin/products', label: 'Produits' }} /><ErrorState error={error} onRetry={reload} /></div>;
  if (!product || !form) return <div className="adm-page"><SkeletonRows rows={10} /></div>;

  const s = PRODUCT_STATUS[product.status];
  const images = product.images;
  const imageOption = (img) => `${img.inGallery ? `Image ${product.images.filter((i) => i.inGallery).indexOf(img) + 1}` : 'Hors galerie'} — ${img.alt || img.kind}`;
  const seoTitle = form.seoTitle || form.displayName || `${form.brand} ${form.name}`;
  const seoDesc = form.seoDescription || form.cardLine || form.summary.slice(0, 160);

  return (
    <div className="adm-page adm-page--editor">
      <PageHeader back={{ to: '/admin/products', label: 'Produits' }} title={product.displayName || product.name}
        badge={<Badge tone={s.tone}>{s.label}</Badge>}
        subtitle={editable ? 'Les modifications de texte s’enregistrent avec le bouton « Enregistrer ».' : 'Lecture seule : votre rôle ne permet pas de modifier les produits.'} />

      {product.status === 'active' && changed.includes('slug') && (
        <Notice tone="warning">Changer l’identifiant d’un produit en ligne casse les liens partagés et les paniers qui le contiennent.</Notice>
      )}

      <div className="adm-detail">
        <div className="adm-detail__main">
          <Card title="Informations">
            <div className="adm-form-grid">
              <Field label="Marque" htmlFor="pe-brand" error={errors.brand} required>
                <input id="pe-brand" className="adm-input" maxLength={100} value={form.brand} onChange={set('brand')} disabled={!editable} />
              </Field>
              <Field label="Nom" htmlFor="pe-name" error={errors.name} required>
                <input id="pe-name" className="adm-input" maxLength={200} value={form.name} onChange={set('name')} disabled={!editable} />
              </Field>
              <div className="adm-form-grid__full">
                <Field label="Nom affiché (titre de la fiche)" htmlFor="pe-display" error={errors.displayName} hint="Vide = marque + nom.">
                  <input id="pe-display" className="adm-input" maxLength={255} value={form.displayName} onChange={set('displayName')} disabled={!editable} />
                </Field>
              </div>
              <div className="adm-form-grid__full">
                <Field label={<>Description courte (cartes produits) <Counter value={form.cardLine} max={160} /></>} htmlFor="pe-line" error={errors.cardLine}>
                  <input id="pe-line" className="adm-input" maxLength={160} value={form.cardLine} onChange={set('cardLine')} disabled={!editable} />
                </Field>
              </div>
              <div className="adm-form-grid__full">
                <Field label="Description (haut de la fiche)" htmlFor="pe-summary" error={errors.summary} required>
                  <textarea id="pe-summary" className="adm-input" rows={4} value={form.summary} onChange={set('summary')} disabled={!editable} />
                </Field>
              </div>
              <div className="adm-form-grid__full">
                <Field label="Description complète (mise en forme, rubrique « Description »)" htmlFor="pe-rich" error={errors.descriptionHtml}
                  hint="Gras, italique, titres, listes et liens https uniquement. Tout autre HTML est retiré.">
                  <RichTextEditor id="pe-rich" value={form.descriptionHtml} resetKey={`${product.id}-${version}`} disabled={!editable}
                    onChange={(html) => setForm((f) => ({ ...f, descriptionHtml: html }))} />
                </Field>
              </div>
            </div>
          </Card>

          <MediaCard product={product} editable={editable} onChanged={refresh} toast={toast} />

          <VariantsCard product={product} editable={editable} canEditCost={can(user, 'editCost')} onChanged={refresh} toast={toast} />

          <Card title="Contenu du soin">
            <div className="adm-form-grid">
              <Field label="Ingrédients (un par ligne)" htmlFor="pe-ingr" error={errors.ingredients}>
                <LinesField id="pe-ingr" value={form.ingredients} onChange={set('ingredients')} disabled={!editable} />
              </Field>
              <Field label="Bienfaits (un par ligne)" htmlFor="pe-ben" error={errors.benefits}>
                <LinesField id="pe-ben" value={form.benefits} onChange={set('benefits')} disabled={!editable} />
              </Field>
              <Field label="Conseils d’utilisation (une étape par ligne)" htmlFor="pe-usage" error={errors.usage}>
                <LinesField id="pe-usage" value={form.usage} onChange={set('usage')} disabled={!editable} />
              </Field>
              <Field label="Types de peau" htmlFor="pe-skin" error={errors.skinTypes}>
                <textarea id="pe-skin" className="adm-input" rows={5} maxLength={255} value={form.skinTypes} onChange={set('skinTypes')} disabled={!editable} />
              </Field>
              <div className="adm-form-grid__full">
                <Field label="Pictos de la fiche (8 maximum)" error={errors.highlights}>
                  <HighlightsEditor value={form.highlights} onChange={set('highlights')} disabled={!editable} />
                </Field>
              </div>
            </div>
          </Card>

          <Card title="Référencement (SEO)">
            <div className="adm-seo-preview" aria-label="Aperçu dans Google">
              <span className="adm-seo-preview__url">mapetitecoree.ma › produits › {form.slug}</span>
              <span className="adm-seo-preview__title">{seoTitle}</span>
              <span className="adm-seo-preview__desc">{seoDesc}</span>
            </div>
            <div className="adm-form-grid adm-mt">
              <div className="adm-form-grid__full">
                <Field label={<>Meta title <Counter value={form.seoTitle} max={70} /></>} htmlFor="pe-seot" error={errors.seoTitle} hint="Vide = nom affiché.">
                  <input id="pe-seot" className="adm-input" maxLength={70} value={form.seoTitle} onChange={set('seoTitle')} disabled={!editable} />
                </Field>
              </div>
              <div className="adm-form-grid__full">
                <Field label={<>Meta description <Counter value={form.seoDescription} max={160} /></>} htmlFor="pe-seod" error={errors.seoDescription} hint="Vide = description courte.">
                  <textarea id="pe-seod" className="adm-input" rows={2} maxLength={160} value={form.seoDescription} onChange={set('seoDescription')} disabled={!editable} />
                </Field>
              </div>
              <Field label="Identifiant URL (slug)" htmlFor="pe-slug" error={errors.slug} hint="Lettres minuscules, chiffres et tirets.">
                <input id="pe-slug" className="adm-input" maxLength={120} value={form.slug} onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-') }))} disabled={!editable} />
              </Field>
              <Field label="Image de partage (réseaux sociaux)" htmlFor="pe-og" error={errors.ogImageId} hint="Vide = image principale.">
                <select id="pe-og" className="adm-input" value={form.ogImageId || ''} onChange={(e) => setForm((f) => ({ ...f, ogImageId: e.target.value ? Number(e.target.value) : null }))} disabled={!editable}>
                  <option value="">Image principale</option>
                  {images.map((img) => <option key={img.id} value={img.mediaId}>{imageOption(img)}</option>)}
                </select>
              </Field>
            </div>
            <p className="adm-footnote adm-mt">Ces balises sont enregistrées et renvoyées par l’API ; leur insertion dans les pages publiques viendra avec le rendu côté serveur (évolution prévue).</p>
          </Card>
        </div>

        <aside className="adm-detail__side">
          <StatusCard product={product} editable={editable} dirty={dirty} onChanged={refresh} onPreview={() => setPreview(true)} toast={toast} />
          <CategoriesCard categories={categories || []} value={form.categoryIds} editable={editable} toast={toast}
            onChange={(ids) => setForm((f) => ({ ...f, categoryIds: ids }))} onCreated={(c) => setCategories([...(categories || []), c])} />
          <Card title="Visuels de l’accueil">
            <Field label="Image au survol (carrousel « produits du moment »)" htmlFor="pe-hover" error={errors.hoverImageId}>
              <select id="pe-hover" className="adm-input" value={form.hoverImageId || ''} disabled={!editable}
                onChange={(e) => setForm((f) => ({ ...f, hoverImageId: e.target.value ? Number(e.target.value) : null }))}>
                <option value="">Aucune</option>
                {images.map((img) => <option key={img.id} value={img.id}>{imageOption(img)}</option>)}
              </select>
            </Field>
            <Field label="Cadrage au survol" htmlFor="pe-hoverpos" error={errors.hoverImagePosition} hint="Ex. « 50% 88% ».">
              <input id="pe-hoverpos" className="adm-input" value={form.hoverImagePosition} onChange={set('hoverImagePosition')} disabled={!editable} />
            </Field>
            <Field label="Image « en situation » (rituel de l’accueil)" htmlFor="pe-scene" error={errors.sceneImageId} hint="Vide = image principale.">
              <select id="pe-scene" className="adm-input" value={form.sceneImageId || ''} disabled={!editable}
                onChange={(e) => setForm((f) => ({ ...f, sceneImageId: e.target.value ? Number(e.target.value) : null }))}>
                <option value="">Image principale</option>
                {images.map((img) => <option key={img.id} value={img.id}>{imageOption(img)}</option>)}
              </select>
            </Field>
          </Card>
        </aside>
      </div>

      {editable && dirty && (
        <div className="adm-savebar" role="region" aria-label="Modifications non enregistrées">
          <span>Modifications non enregistrées ({changed.length})</span>
          <div>
            <Button variant="ghost" icon={Undo2} onClick={() => { setForm(toForm(product)); setErrors({}); setVersion((n) => n + 1); }}>Annuler</Button>
            <Button icon={Save} loading={saving} onClick={save}>Enregistrer</Button>
          </div>
        </div>
      )}
      {preview && <PreviewModal productId={product.id} onClose={() => setPreview(false)} />}
    </div>
  );
}
