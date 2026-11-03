import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Heart, ShoppingCart, Zap, Info, Leaf } from 'lucide-react';
import ProductGallery from './ProductGallery.jsx';
import ProductDetails from './ProductDetails.jsx';
import NamedIcon from './NamedIcon.jsx';
import QuantitySelector from './QuantitySelector.jsx';
import { reassuranceItems } from './Reassurance.jsx';
import VariantPicker from './VariantPicker.jsx';
import ProductMarketing from './ProductMarketing.jsx';
import { formatPrice } from '../utils/currency.js';
import { compareAtPrice, defaultVariant, hasChoice, unitPrice, variantStatus } from '../utils/variants.js';
import { useI18n } from '../i18n/I18nContext.jsx';

/** Engagements en fin de fiche (mobile) : une icône illustrée par engagement, présentation en cartes. */
function MobileTrust({ t }) {
  const items = reassuranceItems(t);
  // Ordre demandé : paiement à la livraison, livraison, produits authentiques, service client.
  const ordered = [items[0], items[2], items[1], items[3]];
  return (
    <section className="pdp-promise" aria-labelledby="pdp-promise-title">
      <h2 className="pdp-promise__title" id="pdp-promise-title">{t('benefits.label')}</h2>
      <ul className="pdp-promise__list">
        {ordered.map(({ icon: Icon, title, text }) => (
          <li key={title} className="pdp-promise__item">
            <span className="pdp-promise__icon" aria-hidden="true"><Icon size={26} strokeWidth={1.5} /></span>
            <strong>{title}</strong>
            <small>{text}</small>
          </li>
        ))}
      </ul>
    </section>
  );
}

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
  const { t, tc, autoDir } = useI18n();
  const mainCat = product.categories[0];
  const catLabel = (id) => tc(categoryLabel(id));
  const categories = product.categories.map(catLabel).join(' · ');
  const changeQty = onQtyChange;
  const toggleFavorite = onToggleFavorite;
  const [variant, setVariant] = useState(() => initialVariant(product));
  const choice = hasChoice(product);
  const status = variantStatus(product, variant);
  const canBuy = status === 'available';
  const price = unitPrice(product, variant);
  const compare = compareAtPrice(product, variant);
  const statusLabel = canBuy ? '' : t(`status.${status}`);
  const handleAdd = () => canBuy && onAdd(variant);
  const handleBuyNow = () => canBuy && onBuyNow(variant);

  return (
    <main className="pdp">
        <nav className="pdp__crumbs container" aria-label={t('pdp.crumbs')}>
          <Link to="/">{t('nav.home')}</Link>
          <ChevronRight size={13} aria-hidden="true" />
          <Link to="/produits">{t('nav.products')}</Link>
          <ChevronRight size={13} aria-hidden="true" />
          <Link to={`/produits?categorie=${mainCat}`}>{catLabel(mainCat)}</Link>
          <ChevronRight size={13} aria-hidden="true" />
          <span aria-current="page">{product.displayName}</span>
        </nav>

        <div className="pdp__layout container">
          <div className="pdp__media">
            <ProductGallery
              key={product.id}
              product={product}
              focusImage={variant?.image || null}
              badge={<span className="pdp__badge"><Leaf size={13} aria-hidden="true" />{catLabel(mainCat)}</span>}
              actions={(
                <button
                  className={`pdp__fav fav-toggle ${isFav ? 'is-active' : ''}`}
                  onClick={() => toggleFavorite(product.id)}
                  aria-pressed={isFav}
                  aria-label={isFav ? t('pdp.favRemove') : t('pdp.favAdd')}
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
              {compare && <s className="pdp__compare"><span className="sr-only">{t('common.compareAt')}</span>{formatPrice(compare)}</s>}
            </p>
            <p className="pdp__desc" dir={autoDir}>{product.summary}</p>

            <ul className="pdp-tiles" aria-label={t('pdp.features')}>
              {product.highlights.map(({ icon, label }) => (
                <li key={label}><NamedIcon name={icon} size={22} strokeWidth={1.4} aria-hidden="true" /><span dir={autoDir}>{label}</span></li>
              ))}
            </ul>

            {choice && <VariantPicker product={product} variant={variant} onChange={setVariant} />}
            {(variant?.sku || !canBuy) && (
              <div className="pdp__variant-info" aria-live="polite">
                {!canBuy && (
                  <p className={`pdp__stock pdp__stock--${status}`}>
                    {statusLabel}
                    {choice && variant?.title ? ` — ${variant.title}` : ''}
                    <small>
                      {status === 'out_of_stock'
                        ? t(choice ? 'pdp.oosVariant' : 'pdp.oosProduct')
                        : t(choice ? 'pdp.unavailableVariant' : 'pdp.unavailableProduct')}
                    </small>
                  </p>
                )}
                {variant?.sku && <p className="pdp__sku">{t('pdp.sku', { sku: variant.sku })}</p>}
              </div>
            )}

            <div className="pdp__buy">
              <div className="pdp__buy-row">
                <QuantitySelector value={qty} onChange={changeQty} max={maxQty} size="buy" />
                <button className="btn pdp__add" onClick={handleAdd} disabled={!canBuy}>
                  <ShoppingCart size={18} aria-hidden="true" /> {canBuy ? t('common.addToCart') : statusLabel}
                </button>
              </div>
              <button className="btn btn--primary btn--block pdp__now" onClick={handleBuyNow} disabled={!canBuy}>
                <Zap size={17} aria-hidden="true" /> {t('pdp.buyNow')}
                {canBuy && <span className="pdp__now-total">· {formatPrice(price * qty)}</span>}
              </button>
            </div>


            {desktop ? (
              <>
                <ul className="pdp__trust">
                  {reassuranceItems(t).map(({ icon: Icon, title, text }) => (
                    <li key={title}>
                      <span className="pdp__trust-icon"><Icon size={19} strokeWidth={1.5} aria-hidden="true" /></span>
                      <span><strong>{title}</strong><small>{text}</small></span>
                    </li>
                  ))}
                </ul>

                {showDemoNotices && (
                  <p className="pdp__note">
                    <Info size={13} aria-hidden="true" />
                    {t('pdp.demoNote')}
                  </p>
                )}

                {/* Landing page : visuels marketing dans la colonne de droite (jamais dans la galerie). */}
                <ProductMarketing product={product} />
              </>
            ) : (
              <>
                {/* Mobile : visuels marketing → description / composition (accordéons) → engagements, tout en bas. */}
                <ProductMarketing product={product} />
                <ProductDetails product={product} desktop={false} />
                {showDemoNotices && (
                  <p className="pdp__note">
                    <Info size={13} aria-hidden="true" />
                    {t('pdp.demoNote')}
                  </p>
                )}
                <MobileTrust t={t} />
              </>
            )}
          </div>
        </div>

        {desktop && <div className="container pdp__details"><ProductDetails product={product} desktop /></div>}
    </main>
  );
}
