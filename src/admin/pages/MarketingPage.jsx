import { Link } from 'react-router-dom';
import { Images } from 'lucide-react';
import { Badge, Card, EmptyState, ErrorState, Notice, PageHeader, SkeletonRows } from '../components/ui.jsx';
import { PRODUCT_STATUS } from '../format.js';
import { useApi, useTitle } from '../hooks.js';

const LANGS = [['fr', 'FR'], ['ar', 'AR'], ['any', 'Sans texte']];

/** Liste des produits et de leurs visuels marketing (par langue). Les photos du produit se gèrent dans la fiche. */
export default function MarketingPage() {
  useTitle('Visuels marketing');
  const { data, error, reload } = useApi('/products', { page_size: 100, ordering: 'position' });

  return (
    <div className="adm-page">
      <PageHeader title="Visuels marketing"
        subtitle="Images de présentation affichées dans la colonne de droite de chaque fiche produit (bannière, bienfaits, utilisation…). Elles ne remplacent jamais les photos du produit." />
      <Notice tone="info">
        Avant / Après : uniquement des photos authentiques, sans retouche ni montage. Un tel visuel ne s’affiche qu’après confirmation explicite.
      </Notice>
      <Card padded={false}>
        {error && <ErrorState error={error} onRetry={reload} />}
        {!data && !error && <SkeletonRows rows={5} />}
        {data && data.items.length === 0 && <EmptyState icon={Images} title="Aucun produit" />}
        {data && data.items.length > 0 && (
          <ul className="adm-mkt-products">
            {data.items.map((p) => {
              const s = PRODUCT_STATUS[p.status];
              return (
                <li key={p.id}>
                  <Link to={`/admin/products/${p.id}/marketing`} className="adm-mkt-products__row">
                    {p.image ? <img src={p.image} alt="" width="52" height="52" /> : <span className="adm-mkt-products__ph" />}
                    <span className="adm-mkt-products__name">
                      <strong>{p.displayName}</strong>
                      <Badge tone={s.tone}>{s.label}</Badge>
                    </span>
                    <span className="adm-mkt-products__counts">
                      {LANGS.map(([code, label]) => {
                        const c = p.marketingCounts?.[code] || { active: 0, total: 0 };
                        return (
                          <span key={code} title={`${c.active} affiché(s) sur ${c.total}`} className={c.active ? 'has-items' : ''}>
                            {label} : {c.active}{c.total > c.active ? ` / ${c.total}` : ''}
                          </span>
                        );
                      })}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </div>
  );
}
