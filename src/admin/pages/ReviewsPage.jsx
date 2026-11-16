import { useState } from 'react';
import { Check, EyeOff, MessageSquareHeart, Pencil, Star, Trash2 } from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import SearchBox from '../components/SearchBox.jsx';
import { Badge, Button, Card, EmptyState, ErrorState, Field, Modal, Notice, PageHeader, Pagination, SkeletonRows } from '../components/ui.jsx';
import { formatDate } from '../format.js';
import { useApi, useTitle, useUrlFilters } from '../hooks.js';
import { can } from '../permissions.js';

const STATUS = { pending: { label: 'En attente', tone: 'warning' }, approved: { label: 'Publié', tone: 'success' } };

function StarsLine({ rating }) {
  return (
    <span className="adm-stars" role="img" aria-label={`${rating} sur 5`}>
      {[1, 2, 3, 4, 5].map((n) => <Star key={n} size={15} aria-hidden="true" className={n <= rating ? 'is-on' : ''} />)}
    </span>
  );
}

/**
 * Admin → Avis clients : avis déposés sur la page « Avis » de la boutique (avis sur la BOUTIQUE, pas sur un produit).
 * Rien n'est publié sans validation : approuver, corriger, dépublier ou supprimer.
 */
export default function ReviewsPage() {
  useTitle('Avis clients');
  const { user } = useAuth();
  const canModerate = can(user, 'moderateReviews');
  const [filters, setFilters] = useUrlFilters({ status: 'pending', search: '', page: '1' });
  const { data, error, loading, reload } = useApi('/reviews', {
    status: filters.status || undefined, search: filters.search || undefined, page: filters.page, page_size: 20,
  });
  const [editing, setEditing] = useState(null);
  const [removing, setRemoving] = useState(null);
  const [message, setMessage] = useState(null);
  const counts = data?.counts || {};

  const setStatus = async (r, status) => {
    setMessage(null);
    try {
      await admin.patch(`/reviews/${r.id}`, { status });
      setMessage({ tone: 'success', text: status === 'approved' ? `L’avis de ${r.name} est publié.` : `L’avis de ${r.name} n’est plus visible dans la boutique.` });
      reload();
    } catch (err) {
      setMessage({ tone: 'danger', text: err.message });
    }
  };

  const tabs = [['pending', 'En attente', counts.pending], ['approved', 'Publiés', counts.approved], ['', 'Tous', null]];

  return (
    <>
      <PageHeader title="Avis clients" subtitle="Avis sur la boutique déposés par les clients. Ils n’apparaissent sur le site qu’après votre validation." />
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
        <SearchBox value={filters.search} onChange={(search) => setFilters({ search })} placeholder="Rechercher (nom, texte)" />
      </div>
      <Card padded={false}>
        {error && <ErrorState error={error} onRetry={reload} />}
        {!data && !error && <SkeletonRows />}
        {data && data.items.length === 0 && (
          <EmptyState icon={MessageSquareHeart} title={filters.status === 'pending' ? 'Aucun avis en attente' : 'Aucun avis'}
            text={filters.status === 'pending' ? 'Les nouveaux avis déposés sur la boutique apparaîtront ici.' : 'Aucun avis ne correspond à ces filtres.'} />
        )}
        {data && data.items.length > 0 && (
          <ul className={`adm-reviews ${loading ? 'is-loading' : ''}`}>
            {data.items.map((r) => (
              <li key={r.id} className="adm-review">
                <div className="adm-review__head">
                  <strong dir="auto">{r.name}</strong>
                  <StarsLine rating={r.rating} />
                  <Badge tone={STATUS[r.status].tone}>{STATUS[r.status].label}</Badge>
                  <span className="adm-muted">
                    Déposé le {formatDate(r.createdAt)}{r.language === 'ar' ? ' · en arabe' : ''}
                  </span>
                </div>
                <p className="adm-review__text" dir="auto">{r.text}</p>
                {canModerate && (
                  <div className="adm-review__actions">
                    {r.status === 'pending'
                      ? <Button size="sm" icon={Check} onClick={() => setStatus(r, 'approved')}>Approuver</Button>
                      : <Button variant="secondary" size="sm" icon={EyeOff} onClick={() => setStatus(r, 'pending')}>Dépublier</Button>}
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
        <ReviewDialog review={editing} onClose={() => setEditing(null)}
          onSaved={(r) => { setEditing(null); setMessage({ tone: 'success', text: `Avis de ${r.name} enregistré.` }); reload(); }} />
      )}
      {removing && (
        <ConfirmDialog title="Supprimer l’avis ?" danger confirmLabel="Supprimer" onClose={() => setRemoving(null)}
          onConfirm={async () => {
            await admin.del(`/reviews/${removing.id}`);
            setMessage({ tone: 'success', text: `L’avis de ${removing.name} a été supprimé.` });
            setRemoving(null);
            reload();
          }}>
          <p>L’avis de {removing.name} sera supprimé définitivement.</p>
        </ConfirmDialog>
      )}
    </>
  );
}

function ReviewDialog({ review, onClose, onSaved }) {
  const [form, setForm] = useState({ name: review.name, rating: review.rating, text: review.text });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      onSaved(await admin.patch(`/reviews/${review.id}`, form));
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  };
  return (
    <Modal open title="Modifier l’avis" onClose={busy ? undefined : onClose}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Annuler</Button>
          <Button loading={busy} onClick={save}>Enregistrer</Button>
        </>
      )}>
      <Notice tone="info">Corrigez seulement les fautes ou un contenu inapproprié : ne changez pas le sens de l’avis du client.</Notice>
      {error && !error.fields && <Notice tone="danger">{error.message}</Notice>}
      <Field label="Nom affiché" htmlFor="rv-name" error={error?.fieldMessage?.('name')}>
        <input id="rv-name" className="adm-input" value={form.name} maxLength={60} dir="auto" onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </Field>
      <Field label="Note" htmlFor="rv-rating" error={error?.fieldMessage?.('rating')}>
        <select id="rv-rating" className="adm-input adm-select" value={form.rating} onChange={(e) => setForm({ ...form, rating: Number(e.target.value) })}>
          {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{'★'.repeat(n)}{'☆'.repeat(5 - n)} ({n}/5)</option>)}
        </select>
      </Field>
      <Field label="Avis" htmlFor="rv-text" error={error?.fieldMessage?.('text')}>
        <textarea id="rv-text" className="adm-input" rows={6} maxLength={1000} dir="auto" value={form.text} onChange={(e) => setForm({ ...form, text: e.target.value })} />
      </Field>
    </Modal>
  );
}
