import { useState } from 'react';
import useMediaQuery from '../hooks/useMediaQuery.js';
import { useNavigate, useParams, Link } from 'react-router-dom';
import ProductView from '../components/ProductView.jsx';
import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { STORE_CONFIG } from '../config/store.js';
import { useCart } from '../context/CartContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { saveDirectOrder } from '../services/orderService.js';

export default function ProductPage() {
  const { id } = useParams();
  const { getProductById, categoryLabel } = useCatalog();
  const product = getProductById(id);
  const navigate = useNavigate();
  const { addItem, favorites, toggleFavorite, maxQty } = useCart();
  const showToast = useToast();
  const [qty, setQty] = useState(1);
  const desktop = useMediaQuery('(min-width: 860px)');

  if (!product) {
    return (
      <>
        <Header />
        <main className="container empty-state">
          <h1>Produit introuvable</h1>
          <p>Ce produit n’existe pas ou n’est plus disponible.</p>
          <Link className="btn btn--primary" to="/produits">Voir nos produits</Link>
        </main>
      </>
    );
  }

  const isFav = favorites.includes(product.id);
  const changeQty = (q) => setQty(Math.max(1, Math.min(maxQty, q)));

  const handleAdd = () => {
    addItem(product.id, qty);
    showToast(`${qty} × ${product.displayName} ajouté${qty > 1 ? 's' : ''} au panier`);
  };
  const handleBuyNow = () => {
    // Achat direct : n'utilise PAS le panier.
    saveDirectOrder({ id: product.id, qty });
    navigate('/commande?mode=direct');
  };

  return (
    <>
      <Header />
      <ProductView
        product={product}
        categoryLabel={categoryLabel}
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
