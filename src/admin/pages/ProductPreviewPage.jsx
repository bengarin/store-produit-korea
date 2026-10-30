import { useState } from 'react';
import { useParams } from 'react-router-dom';
import ProductView from '../../components/ProductView.jsx';
import SiteFooter from '../../components/SiteFooter.jsx';
import useMediaQuery from '../../hooks/useMediaQuery.js';
import { STORE_CONFIG } from '../../config/store.js';
import { normalizeProduct } from '../../services/productService.js';
import { PRODUCT_STATUS } from '../format.js';
import { useApi, useTitle } from '../hooks.js';

/**
 * Aperçu fidèle : le produit arrive au format exact de l'API publique, passe par la même normalisation
 * que la boutique et s'affiche avec le même composant (ProductView). Les boutons d'achat sont inactifs.
 */
export default function ProductPreviewPage() {
  const { id } = useParams();
  const { data, error } = useApi(`/products/${id}/preview`);
  const [qty, setQty] = useState(1);
  const desktop = useMediaQuery('(min-width: 860px)');
  useTitle('Aperçu');

  if (error) return <div className="adm-preview-msg" role="alert">Aperçu indisponible : {error.message}</div>;
  if (!data) return <div className="adm-preview-msg">Chargement de l’aperçu…</div>;

  const product = normalizeProduct(data.product, data.product);
  const status = PRODUCT_STATUS[data.status];
  return (
    <div className="app">
      <div className={`adm-preview-bar adm-preview-bar--${data.status}`} role="note">
        <strong>Aperçu</strong> · statut : {status.label}
        {data.status !== 'active' && ' — non visible des clients'}
        {data.activationErrors.length > 0 && ` · ${data.activationErrors.length} point(s) à compléter avant activation`}
      </div>
      {product.galleryImages.length === 0 ? (
        <main className="container empty-state">
          <h1>{product.displayName}</h1>
          <p>Ajoutez au moins une image pour prévisualiser la fiche.</p>
        </main>
      ) : (
        <ProductView
          product={product}
          categoryLabel={(slug) => data.categoryLabels[slug] || slug}
          qty={qty}
          onQtyChange={(q) => setQty(Math.max(1, Math.min(20, q)))}
          maxQty={20}
          isFav={false}
          onToggleFavorite={() => {}}
          onAdd={() => {}}
          onBuyNow={() => {}}
          showDemoNotices={STORE_CONFIG.showDemoNotices}
          desktop={desktop}
        />
      )}
      <SiteFooter />
    </div>
  );
}
