import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowRight, Boxes, PackageCheck, RotateCcw, ShoppingBag, Truck, Wallet, XCircle } from 'lucide-react';
import { useAuth } from '../auth.jsx';
import SalesChart from '../components/SalesChart.jsx';
import { Badge, ButtonLink, Card, EmptyState, ErrorState, Notice, PageHeader, SkeletonRows, StatusBadge } from '../components/ui.jsx';
import { formatDate, formatInt, formatMoney, todayIso } from '../format.js';
import { useApi, useTitle } from '../hooks.js';
import { can } from '../permissions.js';

const PERIODS = [
  { id: '7', label: '7 jours' },
  { id: '30', label: '30 jours' },
  { id: '90', label: '90 jours' },
  { id: 'custom', label: 'Personnalisée' },
];

function Kpi({ label, value, hint, icon: Icon, tone = 'neutral' }) {
  return (
    <div className={`adm-kpi adm-kpi--${tone}`}>
      <div className="adm-kpi__head">
        <span>{label}</span>
        {Icon && <Icon size={18} aria-hidden="true" />}
      </div>
      <strong className="adm-kpi__value">{value}</strong>
      {hint && <p className="adm-kpi__hint">{hint}</p>}
    </div>
  );
}

export default function DashboardPage() {
  useTitle('Tableau de bord');
  const { user } = useAuth();
  const [period, setPeriod] = useState('30');
  const [custom, setCustom] = useState({ from: todayIso(-29), to: todayIso() });
  const params = period === 'custom' ? custom : { from: todayIso(-(Number(period) - 1)), to: todayIso() };
  const { data, error, loading, reload } = useApi('/analytics/overview', params);
  const k = data?.kpis;

  return (
    <div className="adm-page">
      <PageHeader title="Tableau de bord" subtitle="Chiffres réels issus des commandes enregistrées." />

      <div className="adm-filters" role="group" aria-label="Période">
        <div className="adm-segmented">
          {PERIODS.map((p) => (
            <button key={p.id} type="button" className={period === p.id ? 'is-active' : ''} aria-pressed={period === p.id}
              onClick={() => setPeriod(p.id)}>{p.label}</button>
          ))}
        </div>
        {period === 'custom' && (
          <div className="adm-daterange">
            <label>Du <input type="date" className="adm-input" value={custom.from} max={custom.to}
              onChange={(e) => e.target.value && setCustom((c) => ({ ...c, from: e.target.value }))} /></label>
            <label>au <input type="date" className="adm-input" value={custom.to} min={custom.from}
              onChange={(e) => e.target.value && setCustom((c) => ({ ...c, to: e.target.value }))} /></label>
          </div>
        )}
        {loading && data && <span className="adm-muted">Mise à jour…</span>}
      </div>

      {error && <ErrorState error={error} onRetry={reload} />}
      {!data && loading && <SkeletonRows rows={6} />}

      {data && (
        <>
          {data.stock.unknown > 0 && can(user, 'viewInventory') && (
            <Notice tone="warning" icon={Boxes}
              action={<ButtonLink to="/admin/inventory?state=unknown" variant="secondary">Saisir le stock</ButtonLink>}>
              <strong>{data.stock.unknown} variante{data.stock.unknown > 1 ? 's' : ''} sans stock renseigné.</strong>{' '}
              Elles ne peuvent pas être commandées tant que le stock réel n’est pas saisi.
            </Notice>
          )}

          <div className="adm-kpis">
            <Kpi label="Chiffre d’affaires encaissé" value={formatMoney(k.revenue)} icon={Wallet} tone="primary"
              hint="Commandes livrées (paiement à la livraison)" />
            <Kpi label="Commandes" value={formatInt(k.orders)} icon={ShoppingBag} hint="Toutes, sur la période" />
            <Kpi label="Panier moyen" value={formatMoney(k.averageOrderValue)}
              hint="Hors commandes annulées et retournées" />
            <Kpi label="Ventes (valeur commandée)" value={formatMoney(k.grossSales)}
              hint="Hors annulées et retournées, livrées ou non" />
          </div>

          <div className="adm-status-strip">
            <Link to="/admin/orders?status=pending" className="adm-status-chip adm-status-chip--warning">
              <span>En attente</span><strong>{formatInt(k.pending)}</strong>
            </Link>
            <Link to="/admin/orders?status=shipped" className="adm-status-chip">
              <Truck size={15} aria-hidden="true" /><span>Expédiées</span><strong>{formatInt(k.shipped)}</strong>
            </Link>
            <Link to="/admin/orders?status=delivered" className="adm-status-chip adm-status-chip--success">
              <PackageCheck size={15} aria-hidden="true" /><span>Livrées</span><strong>{formatInt(k.delivered)}</strong>
            </Link>
            <Link to="/admin/orders?status=cancelled" className="adm-status-chip">
              <XCircle size={15} aria-hidden="true" /><span>Annulées</span><strong>{formatInt(k.cancelled)}</strong>
            </Link>
            <Link to="/admin/orders?status=returned" className="adm-status-chip adm-status-chip--danger">
              <RotateCcw size={15} aria-hidden="true" /><span>Retournées</span><strong>{formatInt(k.returned)}</strong>
            </Link>
          </div>

          <Card title="Ventes par jour" actions={<span className="adm-muted">Valeur des commandes (DH)</span>}>
            <SalesChart series={data.series} />
          </Card>

          <div className="adm-grid-2">
            <Card title="Dernières commandes" padded={false}
              actions={data.toProcess > 0 && <Badge tone="warning">{data.toProcess} à traiter</Badge>}>
              {data.recentOrders.length === 0 ? (
                <EmptyState icon={ShoppingBag} title="Aucune commande pour le moment" />
              ) : (
                <ul className="adm-list">
                  {data.recentOrders.map((o) => (
                    <li key={o.id}>
                      <Link to={`/admin/orders/${o.id}`} className="adm-list__row">
                        <div>
                          <strong>{o.number}</strong>
                          <span className="adm-muted">{o.customerName} · {o.city} · {formatDate(o.placedAt)}</span>
                        </div>
                        <div className="adm-list__end">
                          <span className="adm-num">{formatMoney(o.total)}</span>
                          <StatusBadge status={o.status} />
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
              <div className="adm-card__foot"><Link to="/admin/orders" className="adm-link">Toutes les commandes <ArrowRight size={14} /></Link></div>
            </Card>

            <Card title="Alertes de stock" padded={false}
              actions={<span className="adm-muted">{data.stock.outOfStock} rupture · {data.stock.low} bas · {data.stock.unknown} non renseigné</span>}>
              {data.stockAlerts.length === 0 ? (
                <EmptyState icon={PackageCheck} title="Aucune alerte" text="Tous les stocks suivis sont au-dessus de leur seuil." />
              ) : (
                <ul className="adm-list">
                  {data.stockAlerts.map((a) => (
                    <li key={a.variantId}>
                      <Link to={`/admin/inventory?search=${encodeURIComponent(a.productName)}`} className="adm-list__row">
                        <div>
                          <strong>{a.productName}</strong>
                          <span className="adm-muted">{a.variantTitle && a.variantTitle !== 'Par défaut' ? `${a.variantTitle} · ` : ''}seuil d’alerte {a.lowStockThreshold}</span>
                        </div>
                        <div className="adm-list__end">
                          {a.stockQuantity == null ? <Badge tone="neutral-dashed">Non renseigné</Badge>
                            : a.stockQuantity <= 0 ? <Badge tone="danger">Rupture · 0</Badge>
                              : <Badge tone="warning"><AlertTriangle size={12} aria-hidden="true" /> {a.stockQuantity} restant{a.stockQuantity > 1 ? 's' : ''}</Badge>}
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
              <div className="adm-card__foot"><Link to="/admin/inventory" className="adm-link">Gérer le stock <ArrowRight size={14} /></Link></div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
