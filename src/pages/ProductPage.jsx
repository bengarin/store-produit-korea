import { useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Heart, ShoppingCart, Zap, Info, Truck, HandCoins } from 'lucide-react';
import ProductGallery from '../components/ProductGallery.jsx';
import Accordion from '../components/Accordion.jsx';
import QuantitySelector from '../components/QuantitySelector.jsx';
import Header, { CartButton } from '../components/Header.jsx';
import { getProductById, CATALOG_IS_PLACEHOLDER, CATEGORY_LABELS } from '../data/products.js';
import { useCart } from '../context/CartContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { formatPrice } from '../utils/currency.js';
import { saveDirectOrder } from '../utils/order.js';
import { STORE_CONFIG } from '../config/store.js';

export default function ProductPage() {
  const { id } = useParams();
  const product = getProductById(id);
  const navigate = useNavigate();
  const { addItem, count, favorites, toggleFavorite, maxQty } = useCart();
  const showToast = useToast();
  const [qty, setQty] = useState(1);

  if (!product) {
    return (
      <main className="container empty-state">
        <h1>Produit introuvable</h1>
        <p>Ce produit n’existe pas ou n’est plus disponible.</p>
        <Link className="btn btn--primary" to="/produits">Voir nos produits</Link>
      </main>
    );
  }

  const isFav = favorites.includes(product.id);
  const changeQty = (q) => setQty(Math.max(1, Math.min(maxQty, q)));
  const goBack = () => (window.history.state?.idx > 0 ? navigate(-1) : navigate('/produits'));
  const categories = product.categories.map((c) => CATEGORY_LABELS[c]).join(' · ');

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
      <div className="desktop-only"><Header /></div>
      <main className="pdp">
        <nav className="pdp__crumbs container" aria-label="Fil d’Ariane">
          <Link to="/">Accueil</Link>
          <ChevronRight size={13} aria-hidden="true" />
          <Link to="/produits">Nos produits</Link>
          <ChevronRight size={13} aria-hidden="true" />
          <span aria-current="page">{product.displayName}</span>
        </nav>

        <div className="pdp__layout container">
          <div className="pdp__media">
            <ProductGallery key={product.id} product={product} />
            <div className="pdp__controls">
              <button className="icon-btn icon-btn--glass" onClick={goBack} aria-label="Retour">
                <ChevronLeft size={22} strokeWidth={1.7} />
              </button>
              <div className="pdp__controls-right">
                <button
                  className={`icon-btn icon-btn--glass fav-toggle ${isFav ? 'is-active' : ''}`}
                  onClick={() => toggleFavorite(product.id)}
                  aria-pressed={isFav}
                  aria-label={isFav ? 'Retirer des favoris' : 'Ajouter aux favoris'}
                >
                  <Heart size={20} strokeWidth={1.7} />
                </button>
                <div className="icon-btn--glass-wrap pdp__cart"><CartButton count={count} /></div>
              </div>
            </div>
          </div>

          <div className="pdp__info">
            <p className="pdp__cat">{categories}</p>
            <h1 className="pdp__title">{product.displayName}</h1>
            <p className="pdp__price">{formatPrice(product.price)}</p>

            <ul className="pdp__attrs" aria-label="Caractéristiques">
              {product.highlights.map(({ icon: Icon, label }) => (
                <li key={label}><Icon size={15} strokeWidth={1.7} aria-hidden="true" />{label}</li>
              ))}
            </ul>

            <p className="pdp__desc">{product.summary}</p>

            <div className="pdp__accordions">
              <Accordion title="Ingrédients">
                <ul>{product.ingredients.map((x) => <li key={x}>{x}</li>)}</ul>
              </Accordion>
              <Accordion title="Conseils d’utilisation">
                <ol>{product.usage.map((x) => <li key={x}>{x}</li>)}</ol>
              </Accordion>
              <Accordion title="Points forts">
                <ul>{product.benefits.map((x) => <li key={x}>{x}</li>)}</ul>
              </Accordion>
              <Accordion title="Type de peau">
                <p>{product.skinTypes}</p>
              </Accordion>
            </div>

            {CATALOG_IS_PLACEHOLDER && (
              <p className="pdp__note">
                <Info size={13} aria-hidden="true" />
                Contenu et visuel indicatifs : vérifiez la composition sur l’emballage.
              </p>
            )}

            <div className="pdp__buy">
              <div className="pdp__buy-row">
                <QuantitySelector value={qty} onChange={changeQty} max={maxQty} size="buy" />
                <button className="btn btn--outline pdp__add" onClick={handleAdd}>
                  <ShoppingCart size={17} aria-hidden="true" /> Ajouter au panier
                </button>
              </div>
              <button className="btn btn--primary btn--block pdp__now" onClick={handleBuyNow}>
                <Zap size={16} aria-hidden="true" /> Commander maintenant
                <span className="pdp__now-total">· {formatPrice(product.price * qty)}</span>
              </button>
            </div>

            <ul className="pdp__service">
              <li><Truck size={16} strokeWidth={1.6} aria-hidden="true" /> Livraison partout au Maroc · {formatPrice(STORE_CONFIG.deliveryFee)}</li>
              <li><HandCoins size={16} strokeWidth={1.6} aria-hidden="true" /> Paiement à la livraison</li>
            </ul>
          </div>
        </div>
      </main>
    </>
  );
}
