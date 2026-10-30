import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowDownToLine, Boxes, ClipboardList, History, PackagePlus, SlidersHorizontal, X } from 'lucide-react';
import { useAuth } from '../auth.jsx';
import SearchBox from '../components/SearchBox.jsx';
import { AdjustDialog, BulkCountDialog } from '../components/StockDialogs.jsx';
import { Badge, Button, Card, EmptyState, ErrorState, Notice, PageHeader, Pagination, SkeletonRows, StockBadge } from '../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { MOVEMENT_REASONS, STOCK_STATE, formatDate } from '../format.js';
import { useApi, useTitle, useUrlFilters } from '../hooks.js';
import { can } from '../permissions.js';

const STATE_FILTERS = ['unknown', 'out_of_stock', 'low', 'ok'];
const MOVES_PAGE = 25;
const label = (v) => (v.title && v.title !== 'Par défaut' ? v.title : 'Variante unique');

function StockValue({ v }) {
  if (!v.trackInventory) return <span className="adm-muted">Non suivi</span>;
  if (v.stockQuantity == null) return <span className="adm-stock adm-stock--unknown" title="Stock jamais compté">—</span>;
  return <span className={`adm-stock ${v.stockQuantity <= 0 ? 'adm-stock--zero' : ''}`}>{v.stockQuantity}</span>;
}

function StockTab({ f, setF, user }) {
  const showToast = useToast();
  const { data, error, loading, reload } = useApi('/inventory', { page_size: 100, page: Number(f.page) || 1 });
  const [dialog, setDialog] = useState(null); // { variant, mode } | { bulk: true }
  const manage = can(user, 'adjustStock');

  const items = useMemo(() => data?.items || [], [data]);
  const counts = useMemo(() => Object.fromEntries(STATE_FILTERS.map((s) => [s, items.filter((v) => v.state === s).length])), [items]);
  const unknown = items.filter((v) => v.state === 'unknown');
  const term = (f.search || '').toLowerCase();
  const visible = items.filter((v) => (!f.state || v.state === f.state)
    && (!term || `${v.productName} ${v.title} ${v.sku || ''}`.toLowerCase().includes(term)));
  const groups = visible.reduce((acc, v) => {
    (acc[v.productId] ||= { product: v, variants: [] }).variants.push(v);
    return acc;
  }, {});

  const done = (message) => {
    setDialog(null);
    showToast(message);
    reload();
  };

  return (
    <>
      {manage && unknown.length > 0 && (
        <Notice tone="warning" icon={ClipboardList}
          action={<Button onClick={() => setDialog({ bulk: true })} icon={ClipboardList}>Saisie d’inventaire</Button>}>
          <strong>{unknown.length} variante{unknown.length > 1 ? 's' : ''} sans stock renseigné.</strong>{' '}
          Elles ne peuvent pas être commandées tant que le stock réel n’est pas compté.
        </Notice>
      )}

      <div className="adm-filters">
        <SearchBox value={f.search} onChange={(search) => setF({ search })} placeholder="Produit ou SKU" />
        <div className="adm-chips" role="group" aria-label="Filtrer par état du stock">
          <button type="button" className={`adm-chip ${!f.state ? 'is-active' : ''}`} aria-pressed={!f.state} onClick={() => setF({ state: '' })}>
            Tout <span>{items.length}</span>
          </button>
          {STATE_FILTERS.map((s) => (
            <button key={s} type="button" className={`adm-chip adm-chip--${s} ${f.state === s ? 'is-active' : ''}`} aria-pressed={f.state === s}
              onClick={() => setF({ state: f.state === s ? '' : s })}>
              {STOCK_STATE[s].label} <span>{counts[s] ?? 0}</span>
            </button>
          ))}
        </div>
      </div>

      <Card padded={false}>
        {error && <ErrorState error={error} onRetry={reload} />}
        {!data && loading && <SkeletonRows rows={6} />}
        {data && visible.length === 0 && (
          <EmptyState icon={Boxes} title={items.length ? 'Aucune variante ne correspond' : 'Aucun produit'}
            text={items.length ? 'Modifiez la recherche ou le filtre.' : 'Les produits du catalogue apparaîtront ici.'} />
        )}
        {visible.length > 0 && (
          <div className="adm-stock-list">
            {Object.values(groups).map(({ product, variants }) => (
              <section key={product.productId} className="adm-stock-group">
                <header className="adm-stock-group__head">
                  {product.productImage ? <img src={product.productImage} alt="" width="44" height="44" loading="lazy" /> : <span className="adm-thumb" />}
                  <div>
                    <strong>{product.productName}</strong>
                    {product.productStatus !== 'active' && <Badge tone="muted">{product.productStatus === 'draft' ? 'Brouillon' : 'Archivé'}</Badge>}
                  </div>
                </header>
                {variants.map((v) => (
                  <div key={v.id} className={`adm-stock-row adm-stock-row--${v.state}`}>
                    <div className="adm-stock-row__info">
                      <span className="adm-cell-main">{label(v)}</span>
                      <span className="adm-muted adm-cell-sub">SKU {v.sku || '—'} · seuil d’alerte {v.lowStockThreshold}{v.allowBackorder ? ' · vente sans stock autorisée' : ''}</span>
                    </div>
                    <div className="adm-stock-row__qty">
                      <StockValue v={v} />
                      <StockBadge state={v.state} />
                    </div>
                    <div className="adm-stock-row__actions">
                      {manage && v.trackInventory && (v.stockQuantity == null ? (
                        <Button size="sm" icon={PackagePlus} onClick={() => setDialog({ variant: v, mode: 'count' })}>Saisir le stock</Button>
                      ) : (
                        <>
                          <Button size="sm" variant="secondary" icon={ArrowDownToLine} onClick={() => setDialog({ variant: v, mode: 'receive' })}>Réception</Button>
                          <Button size="sm" variant="ghost" icon={SlidersHorizontal} onClick={() => setDialog({ variant: v, mode: 'adjust' })}>Ajuster</Button>
                        </>
                      ))}
                      <Button size="sm" variant="ghost" icon={History} aria-label={`Historique de ${v.productName}`}
                        onClick={() => setF({ tab: 'movements', variant: v.id, vname: `${v.productName}${v.title !== 'Par défaut' ? ` — ${v.title}` : ''}`, state: '', search: '' })} />
                    </div>
                  </div>
                ))}
              </section>
            ))}
          </div>
        )}
        {data && data.total > 100 && (
          <div className="adm-card__foot"><Pagination page={Number(f.page) || 1} pageSize={100} total={data.total} onChange={(p) => setF({ page: p }, { resetPage: false })} /></div>
        )}
      </Card>

      {dialog?.variant && (
        <AdjustDialog variant={dialog.variant} mode={dialog.mode} onClose={() => setDialog(null)}
          onDone={(m) => done(`Stock enregistré : ${m.productName} → ${m.quantityAfter}`)} />
      )}
      {dialog?.bulk && (
        <BulkCountDialog variants={unknown} onClose={() => { setDialog(null); reload(); }}
          onDone={(ok, failed) => { if (!failed) done(`${ok} comptage${ok > 1 ? 's' : ''} enregistré${ok > 1 ? 's' : ''}`); else reload(); }} />
      )}
    </>
  );
}

function MovementsTab({ f, setF }) {
  const page = Number(f.page) || 1;
  const { data, error, loading, reload } = useApi('/inventory/movements', {
    variant: f.variant, reason: f.reason, from: f.from, to: f.to, page, page_size: MOVES_PAGE,
  });
  return (
    <>
      <div className="adm-filters">
        {f.variant && (
          <span className="adm-filter-chip">
            {f.vname || `Variante n° ${f.variant}`}
            <button type="button" aria-label="Retirer le filtre produit" onClick={() => setF({ variant: '', vname: '' })}><X size={14} /></button>
          </span>
        )}
        <select className="adm-input adm-select" value={f.reason || ''} onChange={(e) => setF({ reason: e.target.value })} aria-label="Motif">
          <option value="">Tous les motifs</option>
          {Object.entries(MOVEMENT_REASONS).map(([value, text]) => <option key={value} value={value}>{text}</option>)}
        </select>
        <div className="adm-daterange">
          <label>Du <input type="date" className="adm-input" value={f.from || ''} onChange={(e) => setF({ from: e.target.value })} /></label>
          <label>au <input type="date" className="adm-input" value={f.to || ''} onChange={(e) => setF({ to: e.target.value })} /></label>
        </div>
      </div>
      <Card padded={false}>
        {error && <ErrorState error={error} onRetry={reload} />}
        {!data && loading && <SkeletonRows rows={6} />}
        {data && data.items.length === 0 && <EmptyState icon={History} title="Aucun mouvement" text="Chaque entrée et sortie de stock sera listée ici." />}
        {data && data.items.length > 0 && (
          <div className={`adm-table-wrap ${loading ? 'is-loading' : ''}`}>
            <table className="adm-table adm-table--rows">
              <thead><tr><th>Date</th><th>Produit</th><th>Motif</th><th className="num">Variation</th><th>Stock</th><th>Origine</th><th>Note</th></tr></thead>
              <tbody>
                {data.items.map((m) => (
                  <tr key={m.id}>
                    <td data-label="Date">{formatDate(m.createdAt)}</td>
                    <td data-label="Produit"><span className="adm-cell-main">{m.productName}</span>{m.variantTitle !== 'Par défaut' && <span className="adm-muted adm-cell-sub">{m.variantTitle}</span>}</td>
                    <td data-label="Motif">{m.reasonLabel}</td>
                    <td data-label="Variation" className={`num adm-delta ${m.delta > 0 ? 'is-up' : m.delta < 0 ? 'is-down' : ''}`}>{m.delta > 0 ? `+${m.delta}` : m.delta}</td>
                    <td data-label="Stock" className="adm-nowrap">{m.quantityBefore ?? 'non renseigné'} → <strong>{m.quantityAfter ?? '—'}</strong></td>
                    <td data-label="Origine">
                      {m.orderNumber ? <Link to={`/admin/orders?search=${m.orderNumber}`} className="adm-strong-link">{m.orderNumber}</Link> : m.user || '—'}
                    </td>
                    <td data-label="Note" className="adm-muted">{m.note || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && <div className="adm-card__foot"><Pagination page={page} pageSize={MOVES_PAGE} total={data.total} onChange={(p) => setF({ page: p }, { resetPage: false })} /></div>}
      </Card>
      <p className="adm-footnote">L’historique est en ajout seul : un mouvement ne peut être ni modifié ni supprimé. Pour corriger, faites un nouvel ajustement.</p>
    </>
  );
}

export default function InventoryPage() {
  useTitle('Stock');
  const { user } = useAuth();
  const [f, setF] = useUrlFilters();
  const tab = f.tab === 'movements' ? 'movements' : 'stock';
  return (
    <div className="adm-page">
      <PageHeader title="Stock" subtitle="Quantités réelles par variante. Chaque changement passe par un mouvement tracé." />
      <div className="adm-tabs" role="tablist" aria-label="Stock">
        <button type="button" role="tab" aria-selected={tab === 'stock'} className={tab === 'stock' ? 'is-active' : ''}
          onClick={() => setF({ tab: '', variant: '', vname: '', reason: '', from: '', to: '' })}>Inventaire</button>
        <button type="button" role="tab" aria-selected={tab === 'movements'} className={tab === 'movements' ? 'is-active' : ''}
          onClick={() => setF({ tab: 'movements', state: '', search: '' })}>Historique des mouvements</button>
      </div>
      {tab === 'stock' ? <StockTab f={f} setF={setF} user={user} /> : <MovementsTab f={f} setF={setF} />}
    </div>
  );
}
