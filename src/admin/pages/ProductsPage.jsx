import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Archive, Copy, Eye, Package, Pencil, Plus, RotateCcw, Trash2, Zap } from 'lucide-react';
import { admin } from '../api.js';
import { useAuth } from '../auth.jsx';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import RowMenu from '../components/RowMenu.jsx';
import SearchBox from '../components/SearchBox.jsx';
import { Badge, ButtonLink, Card, EmptyState, ErrorState, PageHeader, Pagination, SkeletonRows } from '../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { PRODUCT_STATUS, formatDate, formatMoney } from '../format.js';
import { useApi, useTitle, useUrlFilters } from '../hooks.js';
import { can } from '../permissions.js';

const PAGE_SIZE = 25;

function StockCell({ p }) {
  if (p.stockUnknown > 0) return <Badge tone="neutral-dashed">Non renseigné</Badge>;
  if (p.totalStock == null) return <span className="adm-muted">—</span>;
  return <span className={p.totalStock <= 0 ? 'adm-text-danger' : ''}>{p.totalStock} en stock</span>;
}

export default function ProductsPage() {
  useTitle('Produits');
  const { user } = useAuth();
  const navigate = useNavigate();
  const showToast = useToast();
  const [f, setF] = useUrlFilters();
  const page = Number(f.page) || 1;
  const { data, error, loading, reload } = useApi('/products', {
    search: f.search, status: f.status, page, page_size: PAGE_SIZE, ordering: 'position',
  });
  const [confirm, setConfirm] = useState(null); // { product, action }
  const edit = can(user, 'editProducts');
  const remove = can(user, 'deleteProducts');

  const setStatus = async (p, status) => {
    await admin.post(`/products/${p.id}/status`, { status });
    showToast(`${p.displayName} : ${PRODUCT_STATUS[status].label.toLowerCase()}`);
    setConfirm(null);
    reload();
  };
  const duplicate = async (p) => {
    try {
      const copy = await admin.post(`/products/${p.id}/duplicate`);
      showToast('Copie créée en brouillon');
      navigate(`/admin/products/${copy.id}`);
    } catch (err) {
      showToast(err.message, 'info');
    }
  };
  const activate = async (p) => {
    try {
      await setStatus(p, 'active');
    } catch (err) {
      const missing = err.fields?.status;
      showToast(missing ? `Activation impossible : ${missing[0]}` : err.message, 'info');
    }
  };

  return (
    <div className="adm-page">
      <PageHeader title="Produits" subtitle="Catalogue de la boutique : brouillons, produits en ligne et archives."
        actions={edit && <ButtonLink to="/admin/products/new" variant="primary" icon={Plus}>Nouveau produit</ButtonLink>} />

      <div className="adm-filters">
        <SearchBox value={f.search} onChange={(search) => setF({ search })} placeholder="Nom, SKU, code-barres ou référence" />
        <div className="adm-segmented" role="group" aria-label="Statut">
          {[['', 'Tous'], ['active', 'Actifs'], ['draft', 'Brouillons'], ['archived', 'Archivés']].map(([value, label]) => (
            <button key={value || 'all'} type="button" className={(f.status || '') === value ? 'is-active' : ''}
              aria-pressed={(f.status || '') === value} onClick={() => setF({ status: value })}>{label}</button>
          ))}
        </div>
      </div>

      <Card padded={false}>
        {error && <ErrorState error={error} onRetry={reload} />}
        {!data && loading && <SkeletonRows rows={6} />}
        {data && data.items.length === 0 && (
          <EmptyState icon={Package} title={f.search || f.status ? 'Aucun produit ne correspond' : 'Aucun produit'}
            text={f.search || f.status ? 'Modifiez la recherche ou le filtre.' : 'Créez votre premier produit.'}
            action={edit && !f.search && <ButtonLink to="/admin/products/new" variant="primary" icon={Plus}>Nouveau produit</ButtonLink>} />
        )}
        {data && data.items.length > 0 && (
          <div className={`adm-table-wrap ${loading ? 'is-loading' : ''}`}>
            <table className="adm-table adm-table--rows adm-products">
              <thead>
                <tr><th aria-label="Image" /><th>Produit</th><th>Statut</th><th className="num">Prix</th><th>Stock</th><th className="num">Variantes</th><th>Modifié</th><th aria-label="Actions" /></tr>
              </thead>
              <tbody>
                {data.items.map((p) => (
                  <tr key={p.id} onClick={() => navigate(`/admin/products/${p.id}`)}>
                    <td className="adm-products__thumb">
                      {p.image ? <img src={p.image} alt="" width="48" height="48" loading="lazy" /> : <span className="adm-thumb" />}
                    </td>
                    <td data-label="Produit">
                      <Link to={`/admin/products/${p.id}`} className="adm-strong-link" onClick={(e) => e.stopPropagation()}>{p.displayName}</Link>
                      <span className="adm-muted adm-cell-sub">{p.sku ? `SKU ${p.sku}` : p.slug}</span>
                    </td>
                    <td data-label="Statut"><Badge tone={PRODUCT_STATUS[p.status].tone}>{PRODUCT_STATUS[p.status].label}</Badge></td>
                    <td data-label="Prix" className="num adm-num">{formatMoney(p.price)}</td>
                    <td data-label="Stock"><StockCell p={p} /></td>
                    <td data-label="Variantes" className="num">{p.variantCount}</td>
                    <td data-label="Modifié">{formatDate(p.updatedAt, { time: false })}</td>
                    <td className="adm-products__menu">
                      <RowMenu label={`Actions pour ${p.displayName}`} items={[
                        { label: edit ? 'Modifier' : 'Voir', icon: Pencil, onClick: () => navigate(`/admin/products/${p.id}`) },
                        { label: 'Aperçu', icon: Eye, onClick: () => window.open(`/admin/preview/products/${p.id}`, '_blank', 'noopener') },
                        edit && p.status !== 'active' && { label: 'Activer', icon: Zap, onClick: () => activate(p) },
                        edit && p.status === 'active' && { label: 'Archiver', icon: Archive, onClick: () => setConfirm({ product: p, action: 'archive' }) },
                        edit && p.status === 'archived' && { label: 'Remettre en brouillon', icon: RotateCcw, onClick: () => setStatus(p, 'draft') },
                        edit && { label: 'Dupliquer', icon: Copy, onClick: () => duplicate(p) },
                        remove && p.status !== 'active' && { label: 'Supprimer', icon: Trash2, danger: true, onClick: () => setConfirm({ product: p, action: 'delete' }) },
                      ]} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && <div className="adm-card__foot"><Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={(p) => setF({ page: p }, { resetPage: false })} /></div>}
      </Card>

      {confirm?.action === 'archive' && (
        <ConfirmDialog title="Archiver ce produit ?" confirmLabel="Archiver" onClose={() => setConfirm(null)}
          onConfirm={() => setStatus(confirm.product, 'archived')}>
          <p><strong>{confirm.product.displayName}</strong> ne sera plus visible sur la boutique. Ses commandes restent intactes ; vous pourrez le réactiver.</p>
        </ConfirmDialog>
      )}
      {confirm?.action === 'delete' && (
        <ConfirmDialog title="Supprimer définitivement ?" confirmLabel="Supprimer" danger onClose={() => setConfirm(null)}
          onConfirm={async () => {
            await admin.del(`/products/${confirm.product.id}`);
            showToast('Produit supprimé');
            setConfirm(null);
            reload();
          }}>
          <p><strong>{confirm.product.displayName}</strong> sera supprimé. Un produit déjà commandé ou ayant un historique de stock ne peut pas être supprimé : archivez-le.</p>
        </ConfirmDialog>
      )}
    </div>
  );
}
