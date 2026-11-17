import { useState } from 'react';
import { BadgeCheck, Check, Pencil, Plus, Star, Trash2, X } from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import SearchBox from '../components/SearchBox.jsx';
import { Badge, Button, Card, EmptyState, ErrorState, Field, Modal, Notice, PageHeader, Pagination, SkeletonRows } from '../components/ui.jsx';
import { formatDate } from '../format.js';
import { useApi, useTitle, useUrlFilters } from '../hooks.js';
import { can } from '../permissions.js';

const STATUS = {
  pending: { label: 'En attente', tone: 'warning' },
  approved: { label: 'Approuvé', tone: 'success' },
  rejected: { label: 'Refusé', tone: 'danger' },
};

function StarsLine({ rating }) {
  return (
    <span className="adm-stars" role="img" aria-label={`${rating} sur 5`}>
      {[1, 2, 3, 4, 5].map((n) => <Star key={n} size={15} aria-hidden="true" className={n <= rating ? 'is-on' : ''} />)}
    </span>
  );
}

/**
 * Admin → Avis produits : avis déposés sur les fiches produit (séparés des avis sur la boutique et des témoignages).
 * Approuver, refuser, corriger, supprimer ; ajouter un VRAI avis client reçu par un autre canal (provenance obligatoire).
 * « Achat vérifié » : calculé par le serveur (commande livrée contenant le produit), jamais coché à la main.
 */
export default function ProductReviewsPage() {
  useTitle('Avis produits');
  const { user } = useAuth();
  const canModerate = can(user, 'moderateReviews');
  const [filters, setFilters] = useUrlFilters({ status: 'pending', product: '', search: '', page: '1' });
  const { data, error, loading, reload } = useApi('/product-reviews', {
    status: filters.status || undefined, product: filters.product || undefined, search: filters.search || undefined,
    page: filters.page, page_size: 20,
  });
  const products = useApi('/products', { page_size: 100, ordering: 'position' });
  const [editing, setEditing] = useState(null); // {} = nouvel avis
  const [removing, setRemoving] = useState(null);
  const [message, setMessage] = useState(null);
  const counts = data?.counts || {};
  const productList = products.data?.items || [];

  const setStatus = async (r, status) => {
    setMessage(null);
    try {
      await admin.patch(`/product-reviews/${r.id}`, { status });
      const verb = { approved: 'est publié', rejected: 'est refusé (non publié)', pending: 'est repassé en attente' }[status];
      setMessage({ tone: 'success', text: `L’avis de ${r.name} sur « ${r.productName} » ${verb}.` });
      reload();
    } catch (err) {
      setMessage({ tone: 'danger', text: err.message });
    }
  };

  const tabs = [['pending', 'En attente', counts.pending], ['approved', 'Approuvés', counts.approved], ['rejected', 'Refusés', counts.rejected], ['', 'Tous', null]];

  return (
    <div className="adm-page">
      <PageHeader title="Avis produits"
        subtitle="Avis laissés sur les fiches produit. Rien n’est publié sans votre validation. Distincts des avis sur la boutique."
        actions={canModerate && <Button icon={Plus} onClick={() => setEditing({})}>Ajouter un avis client</Button>} />
      {message && <Notice tone={message.tone}>{message.text}</Notice>}
      <div className="adm-filters">
        <div className="adm-chips" role="group" aria-label="Statut">
          {tabs.map(([value, label, count]) => (
            <button key={value || 'all'} type="button" className={`adm-chip ${filters.status === value ? 'is-active' : ''}`}
              aria-pressed={filters.status === value} onClick={() => setFilters({ status: value })}>
              {label}{count != null && <span>{count}</span>}
            </button>
          ))}
        </div>
        <select className="adm-input adm-select" aria-label="Produit" value={filters.product} onChange={(e) => setFilters({ product: e.target.value })}>
          <option value="">Tous les produits</option>
          {productList.map((p) => <option key={p.id} value={p.id}>{p.displayName || p.name}</option>)}
        </select>
        <SearchBox value={filters.search} onChange={(search) => setFilters({ search })} placeholder="Rechercher (nom, texte)" />
      </div>
      <Card padded={false}>
        {error && <ErrorState error={error} onRetry={reload} />}
        {!data && !error && <SkeletonRows />}
        {data && data.items.length === 0 && (
          <EmptyState icon={Star} title={filters.status === 'pending' ? 'Aucun avis en attente' : 'Aucun avis'}
            text={filters.status === 'pending' ? 'Les nouveaux avis déposés sur les fiches produit apparaîtront ici.' : 'Aucun avis ne correspond à ces filtres.'} />
        )}
        {data && data.items.length > 0 && (
          <ul className={`adm-reviews ${loading ? 'is-loading' : ''}`}>
            {data.items.map((r) => (
              <li key={r.id} className="adm-review">
                <div className="adm-review__head">
                  <strong dir="auto">{r.name}</strong>
                  <StarsLine rating={r.rating} />
                  <Badge tone={STATUS[r.status].tone}>{STATUS[r.status].label}</Badge>
                  {r.verifiedPurchase && <Badge tone="info"><BadgeCheck size={13} aria-hidden="true" /> Achat vérifié</Badge>}
                </div>
                <p className="adm-review__product">
                  Produit : <strong>{r.productName}</strong>
                  <span className="adm-muted">
                    {' · '}Déposé le {formatDate(r.createdAt)}{r.language === 'ar' ? ' · en arabe' : ''}
                    {r.source === 'admin' ? ` · saisi par l’équipe (${r.sourceNote})` : ' · formulaire de la fiche'}
                    {r.order ? ` · commande ${r.order}` : ''}
                  </span>
                </p>
                <p className="adm-review__text" dir="auto">{r.text}</p>
                {canModerate && (
                  <div className="adm-review__actions">
                    {r.status !== 'approved' && <Button size="sm" icon={Check} onClick={() => setStatus(r, 'approved')}>Approuver</Button>}
                    {r.status !== 'rejected' && <Button variant="secondary" size="sm" icon={X} onClick={() => setStatus(r, 'rejected')}>Refuser</Button>}
                    <Button variant="ghost" size="sm" icon={Pencil} onClick={() => setEditing(r)}>Modifier</Button>
                    {can(user, 'deleteReviews') && (
                      <Button variant="ghost" size="sm" icon={Trash2} onClick={() => setRemoving(r)} aria-label={`Supprimer l’avis de ${r.name}`}>Supprimer</Button>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
      {data && <Pagination page={Number(filters.page)} pageSize={data.pageSize} total={data.total} onChange={(page) => setFilters({ page: String(page) }, { resetPage: false })} />}
      {editing && (
        <ReviewDialog review={editing.id ? editing : null} products={productList} onClose={() => setEditing(null)}
          onSaved={(text) => { setEditing(null); setMessage({ tone: 'success', text }); reload(); }} />
      )}
      {removing && (
        <ConfirmDialog title="Supprimer l’avis ?" danger confirmLabel="Supprimer" onClose={() => setRemoving(null)}
          onConfirm={async () => {
            await admin.del(`/product-reviews/${removing.id}`);
            setMessage({ tone: 'success', text: `L’avis de ${removing.name} a été supprimé.` });
            setRemoving(null);
            reload();
          }}>
          <p>L’avis de {removing.name} sur « {removing.productName} » sera supprimé définitivement. Pour simplement le retirer du site, utilisez « Refuser ».</p>
        </ConfirmDialog>
      )}
    </div>
  );
}

function ReviewDialog({ review, products, onClose, onSaved }) {
  const isNew = !review;
  const [form, setForm] = useState({
    productId: review?.productId || '', name: review?.name || '', rating: review?.rating || 5, text: review?.text || '',
    language: review?.language || 'fr', status: review?.status || 'pending', sourceNote: review?.sourceNote || '',
    orderNumber: review?.order || '', attestation: false,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));
  const err = (k) => error?.fieldMessage?.(k);

  const save = async () => {
    setBusy(true);
    setError(null);
    const body = { ...form, productId: Number(form.productId) || null, rating: Number(form.rating) };
    if (!isNew) delete body.attestation;
    try {
      const saved = isNew ? await admin.post('/product-reviews', body) : await admin.patch(`/product-reviews/${review.id}`, body);
      onSaved(isNew ? `Avis de ${saved.name} ajouté sur « ${saved.productName} » (${STATUS[saved.status].label.toLowerCase()}).` : `Avis de ${saved.name} enregistré.`);
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  };

  return (
    <Modal open size="lg" title={isNew ? 'Ajouter un avis client' : 'Modifier l’avis'} onClose={busy ? undefined : onClose}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Annuler</Button>
          <Button loading={busy} onClick={save}>Enregistrer</Button>
        </>
      )}>
      {isNew ? (
        <Notice tone="info">Uniquement un avis RÉEL envoyé par un client (WhatsApp, e-mail, appel…), recopié fidèlement. Jamais d’avis inventé.</Notice>
      ) : (
        <Notice tone="info">Corrigez seulement les fautes ou un contenu inapproprié : ne changez pas le sens de l’avis du client.</Notice>
      )}
      {error && !error.fields && <Notice tone="danger">{error.message}</Notice>}
      <Field label="Produit" htmlFor="pr-product" required error={err('productId')}>
        <select id="pr-product" className="adm-input" value={form.productId} onChange={set('productId')} disabled={!isNew}>
          <option value="">Choisir un produit…</option>
          {products.map((p) => <option key={p.id} value={p.id}>{p.displayName || p.name}</option>)}
        </select>
      </Field>
      <Field label="Nom affiché" htmlFor="pr-name" required error={err('name')}>
        <input id="pr-name" className="adm-input" value={form.name} maxLength={60} dir="auto" onChange={set('name')} />
      </Field>
      <Field label="Note" htmlFor="pr-rating" error={err('rating')}>
        <select id="pr-rating" className="adm-input adm-select" value={form.rating} onChange={set('rating')}>
          {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{'★'.repeat(n)}{'☆'.repeat(5 - n)} ({n}/5)</option>)}
        </select>
      </Field>
      <Field label="Avis" htmlFor="pr-text" required error={err('text')}>
        <textarea id="pr-text" className="adm-input" rows={5} maxLength={1000} dir="auto" value={form.text} onChange={set('text')} />
      </Field>
      {isNew && (
        <>
          <Field label="Langue de l’avis" htmlFor="pr-lang">
            <select id="pr-lang" className="adm-input adm-select" value={form.language} onChange={set('language')}>
              <option value="fr">Français</option>
              <option value="ar">Arabe</option>
            </select>
          </Field>
          <Field label="Provenance de l’avis" htmlFor="pr-source" required hint="Ex. « Message WhatsApp du 12/11 », « E-mail de la cliente du 03/11 »." error={err('sourceNote')}>
            <input id="pr-source" className="adm-input" value={form.sourceNote} maxLength={200} onChange={set('sourceNote')} />
          </Field>
        </>
      )}
      <Field label="Numéro de commande (facultatif)" htmlFor="pr-order"
        hint="« Achat vérifié » s’affiche seulement si cette commande contient le produit ET est livrée." error={err('orderNumber')}>
        <input id="pr-order" className="adm-input" value={form.orderNumber} maxLength={20} placeholder="MPC-2026-000123" onChange={set('orderNumber')} />
      </Field>
      <Field label="Statut" htmlFor="pr-status" error={err('status')}>
        <select id="pr-status" className="adm-input adm-select" value={form.status} onChange={set('status')}>
          <option value="pending">En attente</option>
          <option value="approved">Approuvé (publié)</option>
          <option value="rejected">Refusé</option>
        </select>
      </Field>
      {isNew && (
        <label className={`adm-check ${err('attestation') ? 'has-error' : ''}`}>
          <input type="checkbox" checked={form.attestation} onChange={set('attestation')} />
          <span>Je confirme que cet avis a été écrit par un vrai client et qu’il est recopié sans modification de sens.</span>
        </label>
      )}
      {err('attestation') && <p className="adm-field__error" role="alert">{err('attestation')}</p>}
    </Modal>
  );
}
