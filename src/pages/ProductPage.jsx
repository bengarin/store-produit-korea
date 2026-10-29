import { useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { ChevronLeft, Heart, ShoppingCart, Zap, Info } from 'lucide-react';
import ProductGallery from '../components/ProductGallery.jsx';
import Accordion from '../components/Accordion.jsx';
import QuantitySelector from '../components/QuantitySelector.jsx';
import Header, { CartButton } from '../components/Header.jsx';
import { getProductById, CATALOG_IS_PLACEHOLDER } from '../data/products.js';
import { useCart } from '../context/CartContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { formatPrice } from '../utils/currency.js';
import { saveDirectOrder } from '../utils/order.js';

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
    <main className="product-page">
      <div className="product-page__media">
        <ProductGallery key={product.id} product={product} />
        <div className="media-overlay">
          <button className="icon-btn icon-btn--glass" onClick={goBack} aria-label="Retour">
            <ChevronLeft size={24} strokeWidth={1.6} />
          </button>
          <div className="media-overlay__right">
            <button
              className={`icon-btn icon-btn--glass fav-toggle ${isFav ? 'is-active' : ''}`}
              onClick={() => toggleFavorite(product.id)}
              aria-pressed={isFav}
              aria-label={isFav ? 'Retirer des favoris' : 'Ajouter aux favoris'}
            >
              <Heart size={22} strokeWidth={1.6} />
            </button>
            <div className="icon-btn--glass-wrap"><CartButton count={count} /></div>
          </div>
        </div>
      </div>

      <div className="product-page__info container">
        <h1 className="product-page__title">{product.brand} – {product.name}</h1>
        <p className="product-page__price">{formatPrice(product.price)}</p>

        <ul className="highlights">
          {product.highlights.map(({ icon: Icon, label }) => (
            <li key={label}>
              <span className="highlights__icon"><Icon size={18} strokeWidth={1.5} /></span>
              {label}
            </li>
          ))}
        </ul>

        <h2 className="section-label">Description</h2>
        <p className="product-page__desc">{product.summary}</p>

        <div className="accordions">
          <Accordion title="Ingrédients clés">
            <ul>{product.ingredients.map((x) => <li key={x}>{x}</li>)}</ul>
          </Accordion>
          <Accordion title="Utilisation">
            <ol>{product.usage.map((x) => <li key={x}>{x}</li>)}</ol>
          </Accordion>
          <Accordion title="Bénéfices">
            <ul>{product.benefits.map((x) => <li key={x}>{x}</li>)}</ul>
          </Accordion>
          <Accordion title="Types de peau">
            <p>{product.skinTypes}</p>
          </Accordion>
        </div>

        {CATALOG_IS_PLACEHOLDER && (
          <p className="demo-note demo-note--left">
            <Info size={14} /> Contenu indicatif : vérifiez la liste d’ingrédients et le mode d’emploi sur l’emballage. En cas de doute, demandez conseil à un professionnel de santé.
          </p>
        )}

        <div className="buy-bar">
          <div className="buy-bar__row">
            <QuantitySelector value={qty} onChange={changeQty} max={maxQty} />
            <button className="btn btn--outline btn--grow" onClick={handleAdd}>
              <ShoppingCart size={18} /> Ajouter au panier
            </button>
          </div>
          <button className="btn btn--primary btn--block btn--lg" onClick={handleBuyNow}>
            <Zap size={17} /> Commander maintenant
          </button>
        </div>
      </div>
    </main>
    </>
  );
}
