import { Link } from 'react-router-dom';
import {
  AlertTriangle, ArrowDownRight, ArrowRight, ArrowUpRight, Boxes, Download, Minus, Package, PackageCheck, Receipt,
  RotateCcw, ShoppingBag, UserPlus, Users, Wallet, XCircle,
} from 'lucide-react';
import { adminUrl } from '../api.js';
import { useAuth } from '../auth.jsx';
import TimeChart, { METRICS } from '../components/analytics/TimeChart.jsx';
import BarList, { formatShare } from '../components/analytics/BarList.jsx';
import { Badge, ButtonLink, Card, EmptyState, ErrorState, Notice, PageHeader, SkeletonRows, StatusBadge } from '../components/ui.jsx';
import { formatDate, formatInt, formatMoney, todayIso } from '../format.js';
import { useApi, useTitle, useUrlFilters } from '../hooks.js';
import { can } from '../permissions.js';

const PRESETS = [
  ['today', 'Aujourd’hui'], ['7d', '7 jours'], ['30d', '30 jours'], ['90d', '90 jours'],
  ['month', 'Ce mois'], ['last_month', 'Mois précédent'], ['year', 'Année en cours'], ['custom', 'Personnalisée'],
];
const TABS = [['ventes', 'Ventes'], ['produits', 'Produits'], ['clients', 'Clients'], ['stock', 'Stock']];
const GRANULARITIES = [['day', 'Jour'], ['week', 'Semaine'], ['month', 'Mois']];
const DEFAULT_VARIANT = 'Par défaut';

const rangeFmt = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
const formatRange = ({ from, to }) => (from === to
  ? rangeFmt.format(new Date(`${from}T00:00:00Z`))
  : `${rangeFmt.format(new Date(`${from}T00:00:00Z`))} → ${rangeFmt.format(new Date(`${to}T00:00:00Z`))}`);
const formatRate = (value) => (value == null ? '—' : formatShare(value));
const formatDecimal = (value) => (value == null ? '—' : value.toLocaleString('fr-FR', { maximumFractionDigits: 2 }));
const variantName = (title) => (title && title !== DEFAULT_VARIANT ? title : '');

/** Évolution vs période précédente. `inverse` : une hausse est une mauvaise nouvelle (annulations, retours). */
function Delta({ change, inverse = false }) {
  if (!change) {
    return (
      <span className="adm-delta adm-delta--none" title="Pas de base de comparaison (période précédente à zéro ou sans objet)">
        n.c.<span className="sr-only"> (non comparable)</span>
      </span>
    );
  }
  const value = change.percent ?? change.points;
  const unit = change.percent != null ? ' %' : ' pt';
  if (value === 0) return <span className="adm-delta adm-delta--none"><Minus size={13} aria-hidden="true" /> 0{unit}</span>;
  const up = value > 0;
  const good = inverse ? !up : up;
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={`adm-delta ${good ? 'adm-delta--good' : 'adm-delta--bad'}`}>
      <Icon size={14} aria-hidden="true" />
      {up ? '+' : '−'}{Math.abs(value).toLocaleString('fr-FR', { maximumFractionDigits: 1 })}{unit}
      <span className="sr-only">{good ? ' (favorable)' : ' (défavorable)'}</span>
    </span>
  );
}

function Kpi({ label, value, previous, change, hint, icon: Icon, inverse, tone = 'neutral' }) {
  return (
    <div className={`adm-kpi adm-kpi--${tone}`}>
      <div className="adm-kpi__head">
        <span>{label}</span>
        {Icon && <Icon size={18} aria-hidden="true" />}
      </div>
      <strong className="adm-kpi__value">{value}</strong>
      <p className="adm-kpi__compare"><Delta change={change} inverse={inverse} /> <span className="adm-muted">vs {previous}</span></p>
      {hint && <p className="adm-kpi__hint">{hint}</p>}
    </div>
  );
}

function ProductTable({ rows, empty, variant = false }) {
  if (!rows.length) return <EmptyState icon={Package} title={empty} />;
  return (
    <div className="adm-table-wrap">
      <table className="adm-table adm-table--compact adm-rank">
        <thead><tr><th>{variant ? 'Variante' : 'Produit'}</th><th className="num">Unités</th><th className="num">Ventes</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={variant ? r.variantId : r.productId}>
              <td>
                <Link to={`/admin/products/${r.productId}`} className="adm-strong-link">{r.name}</Link>
                {variant && variantName(r.variantTitle) && <span className="adm-muted adm-cell-sub">{r.variantTitle}{r.sku ? ` · ${r.sku}` : ''}</span>}
              </td>
              <td className="num">{formatInt(r.units)}</td>
              <td className="num adm-num">{formatMoney(r.sales)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StockList({ rows, kind }) {
  if (!rows.length) return <EmptyState icon={PackageCheck} title="Aucune variante" />;
  return (
    <ul className="adm-list">
      {rows.map((a) => (
        <li key={a.variantId}>
          <Link to={`/admin/inventory?search=${encodeURIComponent(a.productName)}`} className="adm-list__row">
            <div>
              <strong>{a.productName}</strong>
              <span className="adm-muted">{variantName(a.variantTitle) ? `${a.variantTitle} · ` : ''}seuil d’alerte {a.lowStockThreshold}{a.productStatus === 'draft' ? ' · brouillon' : ''}</span>
            </div>
            <div className="adm-list__end">
              {kind === 'unknown' && <Badge tone="neutral-dashed">Non renseigné</Badge>}
              {kind === 'out' && <Badge tone="danger">Épuisé · 0</Badge>}
              {kind === 'low' && <Badge tone="warning"><AlertTriangle size={12} aria-hidden="true" /> {a.stockQuantity} restant{a.stockQuantity > 1 ? 's' : ''}</Badge>}
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export default function DashboardPage() {
  useTitle('Tableau de bord');
  const { user } = useAuth();
  const [f, setF] = useUrlFilters({ preset: '30d', vue: 'ventes', indicateur: 'revenue' });
  const custom = f.preset === 'custom';
  const params = {
    preset: f.preset,
    ...(custom ? { from: f.from || todayIso(-29), to: f.to || todayIso() } : {}),
    ...(f.granularity ? { granularity: f.granularity } : {}),
  };
  const { data, error, loading, reload } = useApi('/analytics/report', params);
  const k = data?.kpis;
  const p = data?.previousKpis;
  const c = data?.changes;
  const metric = METRICS[f.indicateur] ? f.indicateur : 'revenue';
  const tab = TABS.some(([id]) => id === f.vue) ? f.vue : 'ventes';
  const totalStatus = data ? data.statuses.reduce((s, x) => s + x.orders, 0) : 0;

  return (
    <div className="adm-page adm-dashboard">
      <PageHeader title="Tableau de bord" subtitle="Chiffres réels calculés sur les commandes enregistrées (heure du Maroc)."
        actions={<ButtonLink href={adminUrl('/analytics/export', params)} icon={Download} download>Exporter (Excel)</ButtonLink>} />

      <div className="adm-filters adm-filters--dash" role="group" aria-label="Période">
        <div className="adm-segmented adm-segmented--scroll">
          {PRESETS.map(([id, label]) => (
            <button key={id} type="button" className={f.preset === id ? 'is-active' : ''} aria-pressed={f.preset === id}
              onClick={() => setF(id === 'custom'
                ? { preset: id, from: data?.period.from || todayIso(-29), to: data?.period.to || todayIso(), granularity: '' }
                : { preset: id, from: '', to: '', granularity: '' })}>{label}</button>
          ))}
        </div>
        {custom && (
          <div className="adm-daterange">
            <label>Du <input type="date" className="adm-input" value={params.from} max={params.to}
              onChange={(e) => e.target.value && setF({ from: e.target.value, granularity: '' })} /></label>
            <label>au <input type="date" className="adm-input" value={params.to} min={params.from} max={todayIso()}
              onChange={(e) => e.target.value && setF({ to: e.target.value, granularity: '' })} /></label>
          </div>
        )}
        {loading && data && <span className="adm-muted">Mise à jour…</span>}
      </div>
      {data && (
        <p className="adm-period-line">
          <strong>{formatRange(data.period)}</strong>
          <span className="adm-muted"> · comparé à {formatRange(data.previousPeriod)} ({data.previousPeriod.days} jour{data.previousPeriod.days > 1 ? 's' : ''})</span>
        </p>
      )}

      {error && <ErrorState error={error} onRetry={reload} />}
      {!data && loading && <SkeletonRows rows={6} />}

      {data && (
        <>
          {data.stock.counts.unknown > 0 && can(user, 'viewInventory') && (
            <Notice tone="warning" icon={Boxes}
              action={<ButtonLink to="/admin/inventory?state=unknown" variant="secondary">Saisir le stock</ButtonLink>}>
              <strong>{data.stock.counts.unknown} variante{data.stock.counts.unknown > 1 ? 's' : ''} sans stock renseigné.</strong>{' '}
              Elles ne peuvent pas être commandées tant que le stock réel n’est pas saisi.
            </Notice>
          )}

          <div className="adm-kpis adm-kpis--8">
            <Kpi label="Chiffre d’affaires encaissé" value={formatMoney(k.revenue)} previous={formatMoney(p.revenue)} change={c.revenue}
              icon={Wallet} tone="primary" hint={`${formatInt(k.deliveredOrders)} livraison${k.deliveredOrders > 1 ? 's' : ''}, au jour de livraison`} />
            <Kpi label="Commandes" value={formatInt(k.orders)} previous={formatInt(p.orders)} change={c.orders} icon={ShoppingBag}
              hint={`dont ${formatInt(k.validOrders)} valide${k.validOrders > 1 ? 's' : ''} · ventes ${formatMoney(k.grossSales)}`} />
            <Kpi label="Panier moyen" value={formatMoney(k.averageOrderValue)} previous={formatMoney(p.averageOrderValue)}
              change={c.averageOrderValue} icon={Receipt} hint="Commandes valides" />
            <Kpi label="Unités vendues" value={formatInt(k.unitsSold)} previous={formatInt(p.unitsSold)} change={c.unitsSold}
              icon={Package} hint="Commandes valides" />
            <Kpi label="Clients" value={formatInt(k.customers)} previous={formatInt(p.customers)} change={c.customers} icon={Users}
              hint="Au moins une commande valide" />
            <Kpi label="Nouveaux clients" value={formatInt(k.newCustomers)} previous={formatInt(p.newCustomers)} change={c.newCustomers}
              icon={UserPlus} hint={`${formatInt(k.returningCustomers)} client${k.returningCustomers > 1 ? 's' : ''} existant${k.returningCustomers > 1 ? 's' : ''}`} />
            <Kpi label="Taux d’annulation" value={formatRate(k.cancellationRate)} previous={formatRate(p.cancellationRate)}
              change={c.cancellationRate} inverse icon={XCircle} hint={`${formatInt(k.cancelled)} annulée${k.cancelled > 1 ? 's' : ''} / commandes passées`} />
            <Kpi label="Taux de retour" value={formatRate(k.returnRate)} previous={formatRate(p.returnRate)} change={c.returnRate}
              inverse icon={RotateCcw} hint={`${formatInt(k.returned)} retournée${k.returned > 1 ? 's' : ''} / commandes expédiées`} />
          </div>

          <div className="adm-tabs adm-tabs--dash" role="tablist" aria-label="Analyses">
            {TABS.map(([id, label]) => (
              <button key={id} type="button" role="tab" aria-selected={tab === id} className={tab === id ? 'is-active' : ''}
                onClick={() => setF({ vue: id }, { resetPage: false })}>{label}</button>
            ))}
          </div>

          {tab === 'ventes' && (
            <>
              <Card title="Évolution" actions={(
                <div className="adm-chart-controls">
                  <div className="adm-segmented adm-segmented--sm" role="group" aria-label="Indicateur">
                    {Object.entries(METRICS).map(([id, m]) => (
                      <button key={id} type="button" className={metric === id ? 'is-active' : ''} aria-pressed={metric === id}
                        onClick={() => setF({ indicateur: id }, { resetPage: false })}>{m.label}</button>
                    ))}
                  </div>
                  <div className="adm-segmented adm-segmented--sm" role="group" aria-label="Découpage">
                    {GRANULARITIES.map(([id, label]) => (
                      <button key={id} type="button" className={data.granularity === id ? 'is-active' : ''} aria-pressed={data.granularity === id}
                        onClick={() => setF({ granularity: id }, { resetPage: false })}>{label}</button>
                    ))}
                  </div>
                </div>
              )}>
                <p className="adm-muted adm-chart-hint">{METRICS[metric].label} — {METRICS[metric].hint}.</p>
                <TimeChart series={data.series} metric={metric} granularity={data.granularity} />
              </Card>

              <div className="adm-grid-2">
                <Card title="Commandes par statut" actions={<span className="adm-muted">{formatInt(totalStatus)} commande{totalStatus > 1 ? 's' : ''}</span>}>
                  <BarList label="Commandes par statut" empty="Aucune commande sur la période."
                    rows={data.statuses.map((s) => ({
                      key: s.status, label: s.label, value: s.orders, display: formatInt(s.orders),
                      share: totalStatus ? Math.round((s.orders * 1000) / totalStatus) / 10 : null,
                    }))} />
                  <div className="adm-status-strip adm-mt">
                    <Link to="/admin/orders?status=pending" className="adm-status-chip adm-status-chip--warning"><span>À traiter maintenant (toutes dates)</span><strong>{formatInt(data.toProcess)}</strong></Link>
                  </div>
                </Card>
                <Card title="Ventes par catégorie" actions={<span className="adm-muted">Catégorie principale</span>}>
                  <BarList label="Ventes par catégorie" empty="Aucune vente sur la période."
                    rows={data.categories.map((x) => ({
                      key: x.name, label: x.name, value: x.sales, display: formatMoney(x.sales), share: x.share,
                      detail: `${formatInt(x.units)} unité${x.units > 1 ? 's' : ''}`,
                    }))} />
                  <p className="adm-footnote adm-mt">Montants des lignes (avant remise, hors livraison) des commandes valides.</p>
                </Card>
              </div>

              <div className="adm-grid-2">
                <Card title="Mode de paiement">
                  <BarList label="Ventes par mode de paiement" empty="Aucune vente sur la période."
                    rows={data.payments.map((x) => ({
                      key: x.method, label: x.label, value: x.grossSales, display: formatMoney(x.grossSales),
                      detail: `${formatInt(x.orders)} commande${x.orders > 1 ? 's' : ''} valide${x.orders > 1 ? 's' : ''}`,
                    }))} />
                  <p className="adm-footnote adm-mt">La boutique ne propose que le paiement à la livraison pour l’instant.</p>
                </Card>
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
              </div>
            </>
          )}

          {tab === 'produits' && (
            <div className="adm-grid-2">
              <Card title="Les plus vendus" actions={<span className="adm-muted">Unités</span>} padded={false}>
                <ProductTable rows={data.products.topByUnits} empty="Aucune vente sur la période." />
              </Card>
              <Card title="Plus gros chiffre d’affaires" actions={<span className="adm-muted">Ventes</span>} padded={false}>
                <ProductTable rows={data.products.topBySales} empty="Aucune vente sur la période." />
              </Card>
              <Card title="Variantes les plus vendues" padded={false}>
                <ProductTable rows={data.products.topVariants} empty="Aucune vente sur la période." variant />
              </Card>
              <Card title="Les moins performants" actions={<span className="adm-muted">Produits actifs</span>} padded={false}>
                <ProductTable rows={data.products.leastPerforming} empty="Aucun produit actif." />
              </Card>
            </div>
          )}

          {tab === 'clients' && (
            <>
              <div className="adm-kpis adm-kpis--4 adm-kpis--flat">
                <div className="adm-kpi"><div className="adm-kpi__head"><span>Commandes par client</span></div><strong className="adm-kpi__value">{formatDecimal(k.ordersPerCustomer)}</strong><p className="adm-kpi__hint">Commandes valides / clients</p></div>
                <div className="adm-kpi"><div className="adm-kpi__head"><span>Valeur moyenne des commandes</span></div><strong className="adm-kpi__value">{formatMoney(k.averageOrderValue)}</strong><p className="adm-kpi__hint">Panier moyen</p></div>
                <div className="adm-kpi"><div className="adm-kpi__head"><span>Valeur moyenne par client</span></div><strong className="adm-kpi__value">{formatMoney(k.valuePerCustomer)}</strong><p className="adm-kpi__hint">Ventes commandées / clients</p></div>
                <div className="adm-kpi"><div className="adm-kpi__head"><span>Nouveaux / existants</span></div><strong className="adm-kpi__value">{formatInt(k.newCustomers)} / {formatInt(k.returningCustomers)}</strong><p className="adm-kpi__hint">Nouveau = 1re commande valide dans la période</p></div>
              </div>
              <div className="adm-grid-2">
                <Card title="Clients les plus actifs" padded={false}>
                  {data.customers.top.length === 0 ? <EmptyState icon={Users} title="Aucun client sur la période." /> : (
                    <div className="adm-table-wrap">
                      <table className="adm-table adm-table--compact adm-rank">
                        <thead><tr><th>Client</th><th className="num">Commandes</th><th className="num">Montant</th></tr></thead>
                        <tbody>
                          {data.customers.top.map((r) => (
                            <tr key={r.customerId}>
                              <td><Link to={`/admin/customers/${r.customerId}`} className="adm-strong-link">{r.anonymized ? 'Client anonymisé' : r.name}</Link></td>
                              <td className="num">{formatInt(r.orders)}</td>
                              <td className="num adm-num">{formatMoney(r.spent)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Card>
                <Card title="Répartition géographique" actions={<span className="adm-muted">Commandes valides</span>}>
                  <BarList label="Commandes par ville" empty="Aucune commande sur la période."
                    rows={data.customers.cities.map((x) => ({
                      key: x.city, label: x.city, value: x.orders, display: `${formatInt(x.orders)} commande${x.orders > 1 ? 's' : ''}`,
                      share: x.share, detail: formatMoney(x.grossSales),
                    }))} />
                </Card>
              </div>
            </>
          )}

          {tab === 'stock' && (
            <>
              <p className="adm-muted adm-period-line">État actuel du stock (indépendant de la période). Un stock à 0 et un stock non renseigné sont deux situations différentes.</p>
              <div className="adm-grid-3">
                <Card title="Proches de la rupture" actions={<Badge tone="warning">{data.stock.counts.low}</Badge>} padded={false}>
                  <StockList rows={data.stock.low} kind="low" />
                </Card>
                <Card title="Épuisés (stock 0)" actions={<Badge tone="danger">{data.stock.counts.outOfStock}</Badge>} padded={false}>
                  <StockList rows={data.stock.outOfStock} kind="out" />
                </Card>
                <Card title="Stock non renseigné" actions={<Badge tone="neutral-dashed">{data.stock.counts.unknown}</Badge>} padded={false}>
                  <StockList rows={data.stock.unknown} kind="unknown" />
                </Card>
              </div>
              <div className="adm-card__foot"><Link to="/admin/inventory" className="adm-link">Gérer le stock <ArrowRight size={14} /></Link></div>
            </>
          )}

          <details className="adm-definitions">
            <summary>Comment sont calculés ces chiffres ?</summary>
            <ul>
              <li><strong>Montants</strong> : ceux enregistrés dans chaque commande au moment de l’achat (jamais les prix actuels du catalogue). Jours, semaines (lundi → dimanche) et mois à l’heure du Maroc.</li>
              <li><strong>Chiffre d’affaires encaissé</strong> : total (livraison comprise, remise déduite) des commandes livrées, au jour de la livraison. Une commande livrée puis retournée n’y figure plus.</li>
              <li><strong>Commande valide</strong> : ni annulée ni retournée. Commandes, ventes, panier moyen, unités, clients, statuts, catégories et villes sont comptés au jour de la commande.</li>
              <li><strong>Nouveau client</strong> : sa première commande valide (de toute l’histoire de la boutique) a lieu dans la période.</li>
              <li><strong>Taux d’annulation</strong> = annulées / commandes passées · <strong>taux de retour</strong> = retournées / commandes expédiées, livrées ou retournées.</li>
              <li><strong>Comparaison</strong> : période équivalente précédente (même nombre de jours ; mois précédent jusqu’au même jour ; année précédente même intervalle). « n.c. » = non comparable (période précédente à zéro ou sans objet).</li>
              <li><strong>Catégories</strong> : catégorie principale actuelle du produit ; chaque vente n’est comptée qu’une fois.</li>
            </ul>
          </details>
        </>
      )}
    </div>
  );
}
