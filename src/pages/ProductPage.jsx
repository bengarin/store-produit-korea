import { useState } from 'react';
import useMediaQuery from '../hooks/useMediaQuery.js';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { ChevronRight, Heart, ShoppingCart, Zap, Info, Leaf } from 'lucide-react';
import ProductGallery from '../components/ProductGallery.jsx';
import ProductDetails from '../components/ProductDetails.jsx';
import NamedIcon from '../components/NamedIcon.jsx';
import QuantitySelector from '../components/QuantitySelector.jsx';
import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import { REASSURANCE_ITEMS } from '../components/Reassurance.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { STORE_CONFIG } from '../config/store.js';
import { useCart } from '../context/CartContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { formatPrice } from '../utils/currency.js';
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
  const mainCat = product.categories[0];
  const categories = product.categories.map(categoryLabel).join(' · ');

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
      <main className="pdp">
        <nav className="pdp__crumbs container" aria-label="Fil d’Ariane">
          <Link to="/">Accueil</Link>
          <ChevronRight size={13} aria-hidden="true" />
          <Link to="/produits">Nos produits</Link>
          <ChevronRight size={13} aria-hidden="true" />
          <Link to={`/produits?categorie=${mainCat}`}>{categoryLabel(mainCat)}</Link>
          <ChevronRight size={13} aria-hidden="true" />
          <span aria-current="page">{product.displayName}</span>
        </nav>

        <div className="pdp__layout container">
          <div className="pdp__media">
            <ProductGallery
              key={product.id}
              product={product}
              badge={<span className="pdp__badge"><Leaf size={13} aria-hidden="true" />{categoryLabel(mainCat)}</span>}
              actions={(
                <button
                  className={`pdp__fav fav-toggle ${isFav ? 'is-active' : ''}`}
                  onClick={() => toggleFavorite(product.id)}
                  aria-pressed={isFav}
                  aria-label={isFav ? 'Retirer des favoris' : 'Ajouter aux favoris'}
                >
                  <Heart size={20} strokeWidth={1.7} />
                </button>
              )}
            />
          </div>

          <div className="pdp__info">
            <p className="pdp__cat">{categories}</p>
            <h1 className="pdp__title">{product.displayName}</h1>
            <p className="pdp__price">{formatPrice(product.price)}</p>
            <p className="pdp__desc">{product.summary}</p>

            <ul className="pdp-tiles" aria-label="Caractéristiques">
              {product.highlights.map(({ icon, label }) => (
                <li key={label}><NamedIcon name={icon} size={22} strokeWidth={1.4} aria-hidden="true" /><span>{label}</span></li>
              ))}
            </ul>

            <div className="pdp__buy">
              <div className="pdp__buy-row">
                <QuantitySelector value={qty} onChange={changeQty} max={maxQty} size="buy" />
                <button className="btn pdp__add" onClick={handleAdd}>
                  <ShoppingCart size={18} aria-hidden="true" /> Ajouter au panier
                </button>
              </div>
              <button className="btn btn--primary btn--block pdp__now" onClick={handleBuyNow}>
                <Zap size={17} aria-hidden="true" /> Commander maintenant
                <span className="pdp__now-total">· {formatPrice(product.price * qty)}</span>
              </button>
            </div>


            {!desktop && <ProductDetails product={product} desktop={false} />}

            <ul className="pdp__trust">
              {REASSURANCE_ITEMS.map(({ icon: Icon, title, text }) => (
                <li key={title}>
                  <span className="pdp__trust-icon"><Icon size={19} strokeWidth={1.5} aria-hidden="true" /></span>
                  <span><strong>{title}</strong><small>{text}</small></span>
                </li>
              ))}
            </ul>

            {STORE_CONFIG.showDemoNotices && (
              <p className="pdp__note">
                <Info size={13} aria-hidden="true" />
                Description indicative : vérifiez la composition sur l’emballage.
              </p>
            )}
          </div>
        </div>

        {desktop && <div className="container pdp__details"><ProductDetails product={product} desktop /></div>}
      </main>
      <SiteFooter />
    </>
  );
}
