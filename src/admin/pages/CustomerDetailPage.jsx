import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Mail, MapPin, MessageCircle, Phone, ShoppingBag } from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import { Badge, Button, ButtonLink, Card, EmptyState, ErrorState, PageHeader, SkeletonRows, StatusBadge } from '../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { formatDate, formatMoney, formatPhone, whatsappLink } from '../format.js';
import { useApi, useTitle } from '../hooks.js';
import { can } from '../permissions.js';

export default function CustomerDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const showToast = useToast();
  const { data: c, error, reload, setData } = useApi(`/customers/${id}`);
  const [notes, setNotes] = useState(null);
  const [saving, setSaving] = useState(false);
  useTitle(c ? c.fullName : 'Client');
  const manage = can(user, 'manageCustomers');

  if (error) return <div className="adm-page"><PageHeader title="Client" back={{ to: '/admin/customers', label: 'Clients' }} /><ErrorState error={error} onRetry={reload} /></div>;
  if (!c) return <div className="adm-page"><SkeletonRows rows={8} /></div>;
  const wa = whatsappLink(c.phone, `Bonjour ${c.fullName},`);
  const notesValue = notes ?? c.notes;

  const save = async () => {
    setSaving(true);
    try {
      setData(await admin.patch(`/customers/${c.id}`, { notes: notesValue }));
      setNotes(null);
      showToast('Notes enregistrées');
    } catch (err) {
      showToast(err.message, 'info');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="adm-page">
      <PageHeader back={{ to: '/admin/customers', label: 'Clients' }} title={c.fullName}
        subtitle={c.firstOrderAt ? `Client depuis le ${formatDate(c.firstOrderAt, { time: false })}` : null}
        actions={wa && <ButtonLink href={wa} target="_blank" rel="noopener noreferrer" icon={MessageCircle}>WhatsApp</ButtonLink>} />

      <div className="adm-kpis adm-kpis--3">
        <div className="adm-kpi"><div className="adm-kpi__head"><span>Commandes</span></div><strong className="adm-kpi__value">{c.ordersCount}</strong><p className="adm-kpi__hint">Hors annulées</p></div>
        <div className="adm-kpi adm-kpi--primary"><div className="adm-kpi__head"><span>Total encaissé</span></div><strong className="adm-kpi__value">{formatMoney(c.totalSpent)}</strong><p className="adm-kpi__hint">Commandes livrées</p></div>
        <div className="adm-kpi"><div className="adm-kpi__head"><span>Dernière commande</span></div><strong className="adm-kpi__value adm-kpi__value--sm">{formatDate(c.lastOrderAt, { time: false })}</strong></div>
      </div>

      <div className="adm-detail">
        <div className="adm-detail__main">
          <Card title="Historique d’achats" padded={false}>
            {c.orders.length === 0 ? <EmptyState icon={ShoppingBag} title="Aucune commande" /> : (
              <div className="adm-table-wrap">
                <table className="adm-table adm-table--rows">
                  <thead><tr><th>Commande</th><th>Date</th><th className="num">Articles</th><th className="num">Total</th><th>Statut</th></tr></thead>
                  <tbody>
                    {c.orders.map((o) => (
                      <tr key={o.id}>
                        <td data-label="Commande"><Link to={`/admin/orders/${o.id}`} className="adm-strong-link">{o.number}</Link></td>
                        <td data-label="Date">{formatDate(o.placedAt)}</td>
                        <td data-label="Articles" className="num">{o.itemCount}</td>
                        <td data-label="Total" className="num adm-num">{formatMoney(o.total)}</td>
                        <td data-label="Statut"><StatusBadge status={o.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
        <aside className="adm-detail__side">
          <Card title="Coordonnées">
            <p className="adm-line"><Phone size={16} aria-hidden="true" /> <a href={`tel:${c.phone}`}>{formatPhone(c.phone)}</a></p>
            {c.email && <p className="adm-line"><Mail size={16} aria-hidden="true" /> {c.email}</p>}
          </Card>
          <Card title="Adresses de livraison">
            {c.addresses.length === 0 ? <p className="adm-muted">Aucune adresse.</p> : (
              <ul className="adm-addresses">
                {c.addresses.map((a) => (
                  <li key={a.id}>
                    <MapPin size={16} aria-hidden="true" />
                    <div>
                      <strong>{a.fullName}</strong> {a.isDefault && <Badge tone="success">Dernière utilisée</Badge>}
                      <p>{a.address}<br />{a.city} · {formatPhone(a.phone)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="Notes internes">
            <textarea className="adm-input" rows={4} value={notesValue} disabled={!manage} aria-label="Notes internes"
              placeholder={manage ? 'Visibles uniquement par l’équipe' : 'Aucune note'} onChange={(e) => setNotes(e.target.value)} />
            {manage && notes !== null && notes !== c.notes && <Button size="sm" loading={saving} onClick={save} className="adm-mt">Enregistrer</Button>}
          </Card>
        </aside>
      </div>
    </div>
  );
}
