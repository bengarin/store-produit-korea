import { useEffect, useState } from 'react';
import { admin } from '../../api.js';
import { useAuth } from '../../auth.jsx';
import { can } from '../../permissions.js';
import { Button, ButtonLink, Card } from '../ui.jsx';

/**
 * Valeurs de filtre du produit (page produits de la boutique) : groupes et valeurs créés dans Admin → Filtres.
 * Enregistrement séparé du reste de la fiche : seuls ces liens changent (prix, stock, statut intacts).
 */
export default function FiltersCard({ productId, editable, toast }) {
  const { user } = useAuth();
  const [groups, setGroups] = useState(null);
  const [selected, setSelected] = useState([]);
  const [saved, setSaved] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    Promise.all([admin.get('/filters'), admin.get(`/products/${productId}/filters`)])
      .then(([g, p]) => { if (alive) { setGroups(g); setSelected(p.optionIds); setSaved(p.optionIds); } })
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [productId]);

  const dirty = [...selected].sort().join() !== [...saved].sort().join();
  const toggle = (id) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  const save = async () => {
    setBusy(true);
    setError('');
    try {
      const r = await admin.put(`/products/${productId}/filters`, { optionIds: selected });
      setSaved(r.optionIds);
      setSelected(r.optionIds);
      toast('Filtres du produit enregistrés');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Filtres de la boutique"
      actions={can(user, 'manageFilters') && <ButtonLink variant="ghost" to="/admin/filters">Gérer</ButtonLink>}>
      {error && <p className="adm-field__error" role="alert">{error}</p>}
      {!groups && !error && <p className="adm-muted">Chargement…</p>}
      {groups && groups.length === 0 && (
        <p className="adm-muted">Aucun filtre pour l’instant. {can(user, 'manageFilters') ? 'Créez des groupes dans Admin → Filtres.' : 'Un administrateur peut en créer dans Admin → Filtres.'}</p>
      )}
      {groups && groups.map((g) => (
        <fieldset key={g.id} className="adm-filter-pick">
          <legend>{g.name}{!g.isActive && <span className="adm-muted"> · masqué</span>}</legend>
          {g.options.length === 0 && <p className="adm-muted">Aucune valeur.</p>}
          {g.options.map((o) => (
            <label key={o.id} className="adm-check">
              <input type="checkbox" checked={selected.includes(o.id)} disabled={!editable} onChange={() => toggle(o.id)} />
              <span>{o.name}{!o.isActive && <span className="adm-muted"> (masquée)</span>}</span>
            </label>
          ))}
        </fieldset>
      ))}
      {editable && groups && groups.length > 0 && (
        <Button variant={dirty ? 'primary' : 'secondary'} size="sm" loading={busy} disabled={!dirty} onClick={save}>
          Enregistrer les filtres
        </Button>
      )}
    </Card>
  );
}
