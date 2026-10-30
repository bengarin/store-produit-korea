import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { admin } from '../api.js';
import { Button, Card, Field, Notice, PageHeader } from '../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { useApi, useTitle } from '../hooks.js';

/** Création : l'essentiel, puis l'éditeur complet (images, variantes, SEO…) s'ouvre. Toujours en brouillon. */
export default function ProductNewPage() {
  useTitle('Nouveau produit');
  const navigate = useNavigate();
  const showToast = useToast();
  const { data: categories } = useApi('/categories');
  const [form, setForm] = useState({ brand: '', name: '', cardLine: '', price: '', categoryIds: [] });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    try {
      const product = await admin.post('/products', {
        brand: form.brand.trim(), name: form.name.trim(), cardLine: form.cardLine.trim(), categoryIds: form.categoryIds,
        ...(form.price !== '' ? { variant: { price: form.price } } : {}),
      });
      showToast('Produit créé en brouillon');
      navigate(`/admin/products/${product.id}`, { replace: true });
    } catch (err) {
      const fields = err.fields || {};
      setErrors({
        brand: err.fieldMessage('brand'), name: err.fieldMessage('name'), cardLine: err.fieldMessage('cardLine'),
        price: fields.variant?.price?.[0], form: err.fields ? null : err.message,
      });
      setBusy(false);
    }
  };

  return (
    <div className="adm-page adm-page--narrow">
      <PageHeader back={{ to: '/admin/products', label: 'Produits' }} title="Nouveau produit"
        subtitle="Le produit est créé en brouillon : il n’apparaît sur la boutique qu’après activation." />
      <Card>
        <form className="adm-form-grid" onSubmit={submit} noValidate>
          <Field label="Marque" htmlFor="np-brand" error={errors.brand} required>
            <input id="np-brand" className="adm-input" maxLength={100} value={form.brand} onChange={set('brand')} />
          </Field>
          <Field label="Nom du produit" htmlFor="np-name" error={errors.name} required>
            <input id="np-name" className="adm-input" maxLength={200} value={form.name} onChange={set('name')} />
          </Field>
          <div className="adm-form-grid__full">
            <Field label="Description courte (cartes produits)" htmlFor="np-line" error={errors.cardLine} hint="160 caractères maximum.">
              <input id="np-line" className="adm-input" maxLength={160} value={form.cardLine} onChange={set('cardLine')} />
            </Field>
          </div>
          <Field label="Prix de vente (DH)" htmlFor="np-price" error={errors.price} hint="Modifiable ensuite, et par variante.">
            <input id="np-price" className="adm-input" inputMode="decimal" value={form.price} onChange={set('price')} placeholder="0,00" />
          </Field>
          <fieldset className="adm-checklist adm-form-grid__full">
            <legend>Catégories</legend>
            {(categories || []).map((c) => (
              <label key={c.id}>
                <input type="checkbox" checked={form.categoryIds.includes(c.id)}
                  onChange={(e) => setForm((f) => ({ ...f, categoryIds: e.target.checked ? [...f.categoryIds, c.id] : f.categoryIds.filter((x) => x !== c.id) }))} />
                {c.name}
              </label>
            ))}
          </fieldset>
          {errors.form && <div className="adm-form-grid__full"><Notice tone="danger">{errors.form}</Notice></div>}
          <div className="adm-form-grid__full">
            <Button type="submit" icon={Plus} loading={busy}>Créer et continuer</Button>
          </div>
        </form>
      </Card>
      <Notice tone="info">Le stock ne se saisit pas ici : après création, il reste « non renseigné » jusqu’au comptage dans <strong>Stock</strong>.</Notice>
    </div>
  );
}
