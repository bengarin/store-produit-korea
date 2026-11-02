import { useState } from 'react';
import { Languages, Save } from 'lucide-react';
import { admin } from '../../api.js';
import RichTextEditor from '../RichTextEditor.jsx';
import { Button, Card, Field, Notice } from '../ui.jsx';
import { LinesField } from './ContentEditors.jsx';

/** Texte français affiché sous le champ arabe, comme repère pour la traduction (rien si le français est vide). */
function reference(text) {
  if (!text) return undefined;
  return <span className="adm-ar-ref" lang="fr" dir="ltr">Français : {text.length > 140 ? `${text.slice(0, 140)}…` : text}</span>;
}

/** Zone de saisie en arabe (sens droite → gauche). */
function Rtl({ children }) {
  return <div dir="rtl" lang="ar" className="adm-ar-input">{children}</div>;
}

/** Nom arabe d'une catégorie : enregistré tout de suite sur la catégorie (partagée par tous ses produits). */
function CategoryArabicName({ category, editable, onSaved, toast }) {
  const [value, setValue] = useState(category.nameAr || '');
  const [saving, setSaving] = useState(false);
  const dirty = value !== (category.nameAr || '');
  const save = async () => {
    setSaving(true);
    try {
      const saved = await admin.patch(`/categories/${category.id}`, { nameAr: value.trim() });
      onSaved(saved);
      toast(`Nom arabe de « ${category.name} » enregistré`);
    } catch (err) {
      toast(err.fieldMessage?.('nameAr') || err.message, 'info');
    } finally {
      setSaving(false);
    }
  };
  return (
    <div className="adm-ar-highlight">
      <span lang="fr">{category.name}</span>
      <div className="adm-ar-row">
        <Rtl>
          <input className="adm-input" maxLength={100} value={value} disabled={!editable} aria-label={`Nom arabe de la catégorie ${category.name}`}
            onChange={(e) => setValue(e.target.value)} />
        </Rtl>
        {editable && dirty && <Button size="sm" icon={Save} loading={saving} onClick={save}>Enregistrer</Button>}
      </div>
    </div>
  );
}

/**
 * Version arabe du produit : champs facultatifs, indépendants du français (qui n'est jamais modifié ici).
 * Un champ vide = la boutique en arabe affiche le texte français.
 */
export default function ArabicCard({ form, setForm, errors, editable, resetKey, categories = [], onCategorySaved, toast }) {
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e?.target ? e.target.value : e }));
  const setHighlight = (i, labelAr) => setForm((f) => ({
    ...f, highlights: f.highlights.map((h, j) => (j === i ? { ...h, labelAr } : h)),
  }));
  return (
    <Card title={<><Languages size={18} aria-hidden="true" /> Version arabe (العربية)</>}>
      <Notice tone="info">
        Facultatif. Laissé vide, un champ s’affiche en français sur la boutique en arabe. Les noms de marque peuvent rester en latin.
      </Notice>
      <div className="adm-form-grid">
        <div className="adm-form-grid__full">
          <Field label="Nom affiché (arabe)" htmlFor="pe-ar-display" error={errors.displayNameAr} hint={reference(form.displayName || `${form.brand} ${form.name}`.trim())}>
            <Rtl><input id="pe-ar-display" className="adm-input" maxLength={255} value={form.displayNameAr} onChange={set('displayNameAr')} disabled={!editable} /></Rtl>
          </Field>
        </div>
        <div className="adm-form-grid__full">
          <Field label="Description courte (arabe)" htmlFor="pe-ar-line" error={errors.cardLineAr} hint={reference(form.cardLine)}>
            <Rtl><input id="pe-ar-line" className="adm-input" maxLength={160} value={form.cardLineAr} onChange={set('cardLineAr')} disabled={!editable} /></Rtl>
          </Field>
        </div>
        <div className="adm-form-grid__full">
          <Field label="Description (arabe)" htmlFor="pe-ar-summary" error={errors.summaryAr} hint={reference(form.summary)}>
            <Rtl><textarea id="pe-ar-summary" className="adm-input" rows={4} maxLength={5000} value={form.summaryAr} onChange={set('summaryAr')} disabled={!editable} /></Rtl>
          </Field>
        </div>
        <div className="adm-form-grid__full">
          <Field label="Description complète (arabe)" htmlFor="pe-ar-rich" error={errors.descriptionHtmlAr}
            hint="Mêmes règles que le français : gras, italique, titres, listes et liens https uniquement.">
            <Rtl>
              <RichTextEditor id="pe-ar-rich" value={form.descriptionHtmlAr} resetKey={`${resetKey}-ar`} disabled={!editable}
                onChange={(html) => setForm((f) => ({ ...f, descriptionHtmlAr: html }))} />
            </Rtl>
          </Field>
        </div>
        <Field label="Ingrédients (arabe, un par ligne)" htmlFor="pe-ar-ingr" error={errors.ingredientsAr}>
          <Rtl><LinesField id="pe-ar-ingr" value={form.ingredientsAr} onChange={set('ingredientsAr')} disabled={!editable} /></Rtl>
        </Field>
        <Field label="Bienfaits (arabe, un par ligne)" htmlFor="pe-ar-ben" error={errors.benefitsAr}>
          <Rtl><LinesField id="pe-ar-ben" value={form.benefitsAr} onChange={set('benefitsAr')} disabled={!editable} /></Rtl>
        </Field>
        <Field label="Conseils d’utilisation (arabe, une étape par ligne)" htmlFor="pe-ar-usage" error={errors.usageAr}>
          <Rtl><LinesField id="pe-ar-usage" value={form.usageAr} onChange={set('usageAr')} disabled={!editable} /></Rtl>
        </Field>
        <Field label="Types de peau (arabe)" htmlFor="pe-ar-skin" error={errors.skinTypesAr} hint={reference(form.skinTypes)}>
          <Rtl><textarea id="pe-ar-skin" className="adm-input" rows={5} maxLength={255} value={form.skinTypesAr} onChange={set('skinTypesAr')} disabled={!editable} /></Rtl>
        </Field>
        {categories.length > 0 && (
          <div className="adm-form-grid__full">
            <Field label="Catégories (arabe) — enregistrées immédiatement, communes à tous les produits de la catégorie">
              <div className="adm-ar-highlights">
                {categories.map((c) => (
                  <CategoryArabicName key={`${c.id}-${c.nameAr || ''}`} category={c} editable={editable} onSaved={onCategorySaved} toast={toast} />
                ))}
              </div>
            </Field>
          </div>
        )}
        {form.highlights.length > 0 && (
          <div className="adm-form-grid__full">
            <Field label="Pictos (arabe)" error={errors.highlights}>
              <div className="adm-ar-highlights">
                {form.highlights.map((h, i) => (
                  <div key={i} className="adm-ar-highlight">
                    <span lang="fr">{h.label || `Picto ${i + 1}`}</span>
                    <Rtl>
                      <input className="adm-input" maxLength={60} value={h.labelAr || ''} disabled={!editable}
                        aria-label={`Texte arabe du picto ${i + 1}`} onChange={(e) => setHighlight(i, e.target.value)} />
                    </Rtl>
                  </div>
                ))}
              </div>
            </Field>
          </div>
        )}
      </div>
    </Card>
  );
}
