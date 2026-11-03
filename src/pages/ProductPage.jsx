import { useEffect, useState } from 'react';
import useMediaQuery from '../hooks/useMediaQuery.js';
import { useLocation, useNavigate, useParams, Link } from 'react-router-dom';
import ProductView from '../components/ProductView.jsx';
import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { STORE_CONFIG } from '../config/store.js';
import { useCart } from '../context/CartContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { saveDirectOrder } from '../services/orderService.js';
import { defaultVariant, unitPrice, variantLabel } from '../utils/variants.js';
import { productParams, track } from '../analytics/metaPixel.js';

// Fiche déjà comptée pour cette navigation (le double appel des effets en mode strict ne la recompte pas).
let lastViewKey = null;
import { useI18n } from '../i18n/I18nContext.jsx';

export default function ProductPage() {
  const { id } = useParams();
  const { getProductById, categoryLabel, config } = useCatalog();
  const product = getProductById(id);
  const navigate = useNavigate();
  const { addItem, favorites, toggleFavorite, maxQty } = useCart();
  const showToast = useToast();
  const [qty, setQty] = useState(1);
  const desktop = useMediaQuery('(min-width: 860px)');
  const { t } = useI18n();
  const { key: locationKey } = useLocation();

  // ViewContent : une fois par consultation de fiche (prix réel de la variante affichée par défaut).
  useEffect(() => {
    if (!product) return;
    const viewKey = `${locationKey}|${product.id}`;
    if (viewKey === lastViewKey) return;
    lastViewKey = viewKey;
    track('ViewContent', productParams(product, unitPrice(product, defaultVariant(product))));
  }, [product, locationKey]);

  if (!product) {
    return (
      <>
        <Header />
        <main className="container empty-state">
          <h1>{t('pdp.notFoundTitle')}</h1>
          <p>{t('pdp.notFoundText')}</p>
          <Link className="btn btn--primary" to="/produits">{t('pdp.seeProducts')}</Link>
        </main>
      </>
    );
  }

  const isFav = favorites.includes(product.id);
  const changeQty = (q) => setQty(Math.max(1, Math.min(maxQty, q)));

  // `variant` = variante choisie sur la fiche (null en mode démo).
  const handleAdd = (variant) => {
    addItem(product.id, qty, variant?.id);
    const label = variantLabel(product, variant);
    showToast(t('toast.addedQty', { qty, name: `${product.displayName}${label ? ` (${label})` : ''}` }));
  };
  const handleBuyNow = (variant) => {
    // Achat direct : n'utilise PAS le panier.
    saveDirectOrder(variant ? { id: product.id, variantId: variant.id, qty } : { id: product.id, qty });
    navigate('/commande?mode=direct');
  };

  return (
    <>
      <Header />
      <ProductView
        key={product.id}
        product={product}
        categoryLabel={categoryLabel}
        deliveryFee={config?.deliveryFee}
        qty={qty}
        onQtyChange={changeQty}
        maxQty={maxQty}
        isFav={isFav}
        onToggleFavorite={toggleFavorite}
        onAdd={handleAdd}
        onBuyNow={handleBuyNow}
        showDemoNotices={STORE_CONFIG.showDemoNotices}
        desktop={desktop}
      />
      <SiteFooter />
    </>
  );
}
