import { Link, useNavigate } from 'react-router-dom';
import { Download, ShoppingBag } from 'lucide-react';
import { adminUrl } from '../api.js';
import SearchBox from '../components/SearchBox.jsx';
import { ButtonLink, Card, EmptyState, ErrorState, PageHeader, Pagination, PaymentBadge, SkeletonRows, StatusBadge } from '../components/ui.jsx';
import { ORDER_STATUS, PAYMENT_STATUS, formatDate, formatMoney, formatPhone } from '../format.js';
import { useApi, useTitle, useUrlFilters } from '../hooks.js';

const PAGE_SIZE = 25;

export default function OrdersPage() {
  useTitle('Commandes');
  const navigate = useNavigate();
  const [f, setF] = useUrlFilters();
  const page = Number(f.page) || 1;
  const filters = { status: f.status, payment: f.payment, from: f.from, to: f.to, search: f.search };
  const { data, error, loading, reload } = useApi('/orders', { ...filters, page, page_size: PAGE_SIZE });
  const active = Object.values(filters).some(Boolean);

  return (
    <div className="adm-page">
      <PageHeader
        title="Commandes"
        subtitle="Paiement à la livraison · statuts, factures et export."
        actions={(
          <ButtonLink href={adminUrl('/orders/export.xlsx', filters)} icon={Download} download>
            Exporter (Excel)
          </ButtonLink>
        )}
      />

      <div className="adm-filters">
        <SearchBox value={f.search} onChange={(search) => setF({ search })} placeholder="N° de commande, nom ou téléphone" />
        <select className="adm-input adm-select" value={f.status || ''} onChange={(e) => setF({ status: e.target.value })} aria-label="Statut">
          <option value="">Tous les statuts</option>
          {Object.entries(ORDER_STATUS).map(([value, s]) => <option key={value} value={value}>{s.label}</option>)}
        </select>
        <select className="adm-input adm-select" value={f.payment || ''} onChange={(e) => setF({ payment: e.target.value })} aria-label="Paiement">
          <option value="">Tous les paiements</option>
          {Object.entries(PAYMENT_STATUS).map(([value, s]) => <option key={value} value={value}>{s.label}</option>)}
        </select>
        <div className="adm-daterange">
          <label>Du <input type="date" className="adm-input" value={f.from || ''} onChange={(e) => setF({ from: e.target.value })} /></label>
          <label>au <input type="date" className="adm-input" value={f.to || ''} onChange={(e) => setF({ to: e.target.value })} /></label>
        </div>
        {active && <button type="button" className="adm-link-btn" onClick={() => setF({ status: '', payment: '', from: '', to: '', search: '' })}>Effacer les filtres</button>}
      </div>

      <Card padded={false}>
        {error && <ErrorState error={error} onRetry={reload} />}
        {!data && loading && <SkeletonRows rows={8} />}
        {data && data.items.length === 0 && (
          <EmptyState icon={ShoppingBag} title={active ? 'Aucune commande ne correspond' : 'Aucune commande pour le moment'}
            text={active ? 'Modifiez ou effacez les filtres.' : 'Les commandes passées sur la boutique apparaîtront ici.'} />
        )}
        {data && data.items.length > 0 && (
          <div className={`adm-table-wrap ${loading ? 'is-loading' : ''}`}>
            <table className="adm-table adm-table--rows">
              <thead>
                <tr>
                  <th>Commande</th><th>Date</th><th>Client</th><th>Ville</th>
                  <th className="num">Articles</th><th className="num">Total</th><th>Paiement</th><th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((o) => (
                  <tr key={o.id} onClick={() => navigate(`/admin/orders/${o.id}`)}>
                    <td data-label="Commande"><Link to={`/admin/orders/${o.id}`} onClick={(e) => e.stopPropagation()} className="adm-strong-link">{o.number}</Link></td>
                    <td data-label="Date">{formatDate(o.placedAt)}</td>
                    <td data-label="Client"><span className="adm-cell-main">{o.customerName}</span><span className="adm-muted adm-cell-sub">{formatPhone(o.phone)}</span></td>
                    <td data-label="Ville">{o.city}</td>
                    <td data-label="Articles" className="num">{o.itemCount}</td>
                    <td data-label="Total" className="num adm-num">{formatMoney(o.total)}</td>
                    <td data-label="Paiement"><PaymentBadge status={o.paymentStatus} /></td>
                    <td data-label="Statut"><StatusBadge status={o.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && <div className="adm-card__foot"><Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={(p) => setF({ page: p }, { resetPage: false })} /></div>}
      </Card>
    </div>
  );
}
