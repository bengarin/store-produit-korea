import { Link, useNavigate } from 'react-router-dom';
import { Users } from 'lucide-react';
import SearchBox from '../components/SearchBox.jsx';
import { Card, EmptyState, ErrorState, PageHeader, Pagination, SkeletonRows } from '../components/ui.jsx';
import { formatDate, formatMoney, formatPhone } from '../format.js';
import { useApi, useTitle, useUrlFilters } from '../hooks.js';

const PAGE_SIZE = 25;
const ORDERINGS = [
  { value: '-last_order_at', label: 'Dernière commande' },
  { value: '-total_spent', label: 'Total dépensé' },
  { value: '-orders_count', label: 'Nombre de commandes' },
  { value: 'full_name', label: 'Nom (A → Z)' },
];

export default function CustomersPage() {
  useTitle('Clients');
  const navigate = useNavigate();
  const [f, setF] = useUrlFilters();
  const page = Number(f.page) || 1;
  const { data, error, loading, reload } = useApi('/customers', { search: f.search, ordering: f.ordering, page, page_size: PAGE_SIZE });

  return (
    <div className="adm-page">
      <PageHeader title="Clients" subtitle="Identifiés par leur numéro de téléphone marocain." />
      <div className="adm-filters">
        <SearchBox value={f.search} onChange={(search) => setF({ search })} placeholder="Nom ou téléphone" />
        <label className="adm-inline-label">Trier par
          <select className="adm-input adm-select" value={f.ordering || '-last_order_at'} onChange={(e) => setF({ ordering: e.target.value })}>
            {ORDERINGS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>
      </div>
      <Card padded={false}>
        {error && <ErrorState error={error} onRetry={reload} />}
        {!data && loading && <SkeletonRows rows={8} />}
        {data && data.items.length === 0 && (
          <EmptyState icon={Users} title={f.search ? 'Aucun client trouvé' : 'Aucun client pour le moment'}
            text={f.search ? 'Vérifiez le nom ou le numéro.' : 'Un client est créé à sa première commande.'} />
        )}
        {data && data.items.length > 0 && (
          <div className={`adm-table-wrap ${loading ? 'is-loading' : ''}`}>
            <table className="adm-table adm-table--rows">
              <thead><tr><th>Client</th><th>Téléphone</th><th className="num">Commandes</th><th className="num">Total encaissé</th><th>Dernière commande</th></tr></thead>
              <tbody>
                {data.items.map((c) => (
                  <tr key={c.id} onClick={() => navigate(`/admin/customers/${c.id}`)}>
                    <td data-label="Client"><Link to={`/admin/customers/${c.id}`} className="adm-strong-link" onClick={(e) => e.stopPropagation()}>{c.fullName}</Link></td>
                    <td data-label="Téléphone">{formatPhone(c.phone)}</td>
                    <td data-label="Commandes" className="num">{c.ordersCount}</td>
                    <td data-label="Total encaissé" className="num adm-num">{formatMoney(c.totalSpent)}</td>
                    <td data-label="Dernière commande">{formatDate(c.lastOrderAt, { time: false })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && <div className="adm-card__foot"><Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={(p) => setF({ page: p }, { resetPage: false })} /></div>}
      </Card>
      <p className="adm-footnote">« Commandes » = commandes non annulées · « Total encaissé » = commandes livrées (paiement à la livraison).</p>
    </div>
  );
}
