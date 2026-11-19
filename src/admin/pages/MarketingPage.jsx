import { Link, useSearchParams } from 'react-router-dom';
import { Images } from 'lucide-react';
import { Badge, Card, EmptyState, ErrorState, Notice, PageHeader, SkeletonRows } from '../components/ui.jsx';
import { PRODUCT_STATUS } from '../format.js';
import { useApi, useTitle } from '../hooks.js';
import { useAuth } from '../auth.jsx';
import { can } from '../permissions.js';
import HeroSlidesManager from '../components/HeroSlidesManager.jsx';

const LANGS = [['fr', 'FR'], ['ar', 'AR'], ['any', 'Sans texte']];

const TABS = [['accueil', 'Bannière de l’accueil'], ['produits', 'Fiches produits']];

/**
 * Visuels marketing : bannière de l'accueil (diapositives) et visuels des fiches produits (par langue).
 * Les photos du produit se gèrent dans la fiche.
 */
export default function MarketingPage() {
  useTitle('Visuels marketing');
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = params.get('onglet') === 'produits' ? 'produits' : 'accueil';

  return (
    <div className="adm-page">
      <PageHeader title="Visuels marketing"
        subtitle="Bannière principale de l’accueil et images de présentation des fiches produits (bannière, bienfaits, utilisation…). Elles ne remplacent jamais les photos du produit." />
      <div className="adm-tabs" role="tablist" aria-label="Type de visuels">
        {TABS.map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} className={tab === id ? 'is-active' : ''}
            onClick={() => setParams(id === 'accueil' ? {} : { onglet: id }, { replace: true })}>
            {label}
          </button>
        ))}
      </div>
      {tab === 'accueil'
        ? <HeroSlidesManager editable={can(user, 'editProducts')} canDelete={can(user, 'deleteProducts')} />
        : <ProductMarketingList />}
    </div>
  );
}

function ProductMarketingList() {
  const { data, error, reload } = useApi('/products', { page_size: 100, ordering: 'position' });

  return (
    <>
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
    </>
  );
}
