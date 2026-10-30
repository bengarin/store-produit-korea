import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Heart, ShoppingCart, Zap, Info, Leaf } from 'lucide-react';
import ProductGallery from './ProductGallery.jsx';
import ProductDetails from './ProductDetails.jsx';
import NamedIcon from './NamedIcon.jsx';
import QuantitySelector from './QuantitySelector.jsx';
import { REASSURANCE_ITEMS } from './Reassurance.jsx';
import VariantPicker from './VariantPicker.jsx';
import { formatPrice } from '../utils/currency.js';
import { STATUS_LABELS, compareAtPrice, defaultVariant, hasChoice, unitPrice, variantStatus } from '../utils/variants.js';

/** Variante affichée à l'ouverture : celle par défaut si elle est disponible, sinon la 1re disponible. */
function initialVariant(product) {
  const fallback = defaultVariant(product);
  if (!hasChoice(product) || variantStatus(product, fallback) === 'available') return fallback;
  return product.variants.find((v) => variantStatus(product, v) === 'available') || fallback;
}

/**
 * Fiche produit (présentation seule). Utilisée par la boutique (ProductPage) ET par l'aperçu de
 * l'administration : ce que l'équipe prévisualise est exactement ce que voient les clients.
 * Le choix de variante vit ici ; `onAdd(variant)` et `onBuyNow(variant)` reçoivent la variante choisie
 * (null en mode démo, sans variantes).
 */
export default function ProductView({
  product, categoryLabel, qty, onQtyChange, maxQty, isFav, onToggleFavorite, onAdd, onBuyNow, showDemoNotices, desktop,
}) {
  const mainCat = product.categories[0];
  const categories = product.categories.map(categoryLabel).join(' · ');
  const changeQty = onQtyChange;
  const toggleFavorite = onToggleFavorite;
  const [variant, setVariant] = useState(() => initialVariant(product));
  const choice = hasChoice(product);
  const status = variantStatus(product, variant);
  const canBuy = status === 'available';
  const price = unitPrice(product, variant);
  const compare = compareAtPrice(product, variant);
  const handleAdd = () => canBuy && onAdd(variant);
  const handleBuyNow = () => canBuy && onBuyNow(variant);

  return (
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
              focusImage={variant?.image || null}
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
            <p className="pdp__price">
              {formatPrice(price)}
              {compare && <s className="pdp__compare"><span className="sr-only">Prix habituel : </span>{formatPrice(compare)}</s>}
            </p>
            <p className="pdp__desc">{product.summary}</p>

            <ul className="pdp-tiles" aria-label="Caractéristiques">
              {product.highlights.map(({ icon, label }) => (
                <li key={label}><NamedIcon name={icon} size={22} strokeWidth={1.4} aria-hidden="true" /><span>{label}</span></li>
              ))}
            </ul>

            {choice && <VariantPicker product={product} variant={variant} onChange={setVariant} />}
            {(variant?.sku || !canBuy) && (
              <div className="pdp__variant-info" aria-live="polite">
                {!canBuy && (
                  <p className={`pdp__stock pdp__stock--${status}`}>
                    {STATUS_LABELS[status]}
                    {choice && variant?.title ? ` — ${variant.title}` : ''}
                    <small>
                      {status === 'out_of_stock'
                        ? `${choice ? 'Cette variante' : 'Ce produit'} n’est plus en stock pour le moment.`
                        : `${choice ? 'Cette variante ne peut pas être commandée' : 'Ce produit ne peut pas être commandé'} pour le moment.`}
                    </small>
                  </p>
                )}
                {variant?.sku && <p className="pdp__sku">Réf. {variant.sku}</p>}
              </div>
            )}

            <div className="pdp__buy">
              <div className="pdp__buy-row">
                <QuantitySelector value={qty} onChange={changeQty} max={maxQty} size="buy" />
                <button className="btn pdp__add" onClick={handleAdd} disabled={!canBuy}>
                  <ShoppingCart size={18} aria-hidden="true" /> {canBuy ? 'Ajouter au panier' : STATUS_LABELS[status]}
                </button>
              </div>
              <button className="btn btn--primary btn--block pdp__now" onClick={handleBuyNow} disabled={!canBuy}>
                <Zap size={17} aria-hidden="true" /> Commander maintenant
                {canBuy && <span className="pdp__now-total">· {formatPrice(price * qty)}</span>}
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

            {showDemoNotices && (
              <p className="pdp__note">
                <Info size={13} aria-hidden="true" />
                Description indicative : vérifiez la composition sur l’emballage.
              </p>
            )}
          </div>
        </div>

        {desktop && <div className="container pdp__details"><ProductDetails product={product} desktop /></div>}
    </main>
  );
}
