import { useApi } from '../../hooks.js';
import { COUNTRIES, collectionIssues } from '../../countries.js';
import { ButtonLink, Card, Field } from '../ui.jsx';
import { linesToList } from './ContentEditors.jsx';

/**
 * Origine et collections du produit (enregistrées avec le bouton « Enregistrer » de la fiche).
 * Une seule fiche et un seul stock, même dans plusieurs collections. Une collection dont la règle n'est pas
 * respectée (pays de fabrication, ingrédients) est grisée, avec la raison ; le serveur vérifie aussi.
 */
export default function CollectionsCard({ form, setForm, editable, errors }) {
  const { data: collections } = useApi('/collections');
  const info = { origin: form.originCountry, ingredients: linesToList(form.ingredients) };
  const toggle = (id) => setForm((f) => ({
    ...f, collectionIds: f.collectionIds.includes(id) ? f.collectionIds.filter((x) => x !== id) : [...f.collectionIds, id],
  }));
  return (
    <Card title="Origine et collections">
      <Field label="Pays de fabrication" htmlFor="pe-origin" error={errors.originCountry}
        hint="Tel qu’écrit sur l’emballage (« Made in … »). Laissez « Non renseigné » si vous ne l’avez pas vérifié.">
        <select id="pe-origin" className="adm-input" value={form.originCountry} disabled={!editable}
          onChange={(e) => setForm((f) => ({ ...f, originCountry: e.target.value }))}>
          <option value="">Non renseigné</option>
          {COUNTRIES.map(([code, name]) => <option key={code} value={code}>{name}</option>)}
        </select>
      </Field>
      <fieldset className="adm-collections">
        <legend className="adm-field__label">Collections de la boutique</legend>
        {!collections && <p className="adm-muted">Chargement…</p>}
        {collections && collections.length === 0 && <p className="adm-muted">Aucune collection.</p>}
        {collections && collections.map((c) => {
          const checked = form.collectionIds.includes(c.id);
          const issues = collectionIssues(c, info);
          return (
            <label key={c.id} className={`adm-check adm-collection-option ${issues.length && checked ? 'has-error' : ''}`}>
              <input type="checkbox" checked={checked} disabled={!editable || (!checked && issues.length > 0)} onChange={() => toggle(c.id)} />
              <span>
                <strong>{c.name}</strong>{!c.isActive && <span className="adm-muted"> (masquée)</span>}
                {issues.length > 0 && <span className="adm-collection-option__why">Non disponible : {issues.join(' ; ')}.</span>}
              </span>
            </label>
          );
        })}
        {errors.collectionIds && <p className="adm-field__error" role="alert">{errors.collectionIds}</p>}
      </fieldset>
      <ButtonLink to="/admin/collections" variant="ghost">Gérer les collections</ButtonLink>
    </Card>
  );
}
