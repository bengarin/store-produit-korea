import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Check, Heart, PackageOpen, ShoppingCart } from 'lucide-react';
import ProductImage from './ProductImage.jsx';
import Stars from './Stars.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { useCart } from '../context/CartContext.jsx';
import useQuickAdd from '../hooks/useQuickAdd.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { formatPrice } from '../utils/currency.js';
import { hasChoice, productStatus } from '../utils/variants.js';

const MAX_CARDS = 4;

/**
 * Accueil — « Nos collections » : un onglet par collection visible (Admin → Collections, dans leur ordre),
 * puis jusqu'à 4 produits EN LIGNE de la collection choisie (4 par ligne sur ordinateur, 2 sur mobile).
 * - Données réelles uniquement : photo, nom, prix, état du stock, panier et favoris existants.
 * - Étoiles seulement s'il existe des avis produits APPROUVÉS (fournis par le serveur) ; sinon rien.
 * - Collection sans produit en ligne : message « bientôt », jamais de produit fictif.
 */
export default function HomeEssentials() {
  const { homeCollections, products } = useCatalog();
  const { t } = useI18n();
  const [selected, setSelected] = useState(null);
  const tabRefs = useRef([]);
  const uid = useId();

  const active = homeCollections.find((c) => c.id === selected) || homeCollections[0];
  const items = useMemo(
    () => (active ? products.filter((p) => p.collections.includes(active.id)).slice(0, MAX_CARDS) : []),
    [active, products],
  );
  if (!active) return null;

  const tabId = (c) => `${uid}-tab-${c.id}`;
  const panelId = `${uid}-panel`;
  // Clavier : flèches (sens inversé en arabe), Début, Fin — comme un groupe d'onglets standard.
  const onKeyDown = (e, index) => {
    const rtl = document.documentElement.dir === 'rtl';
    const step = { ArrowRight: rtl ? -1 : 1, ArrowLeft: rtl ? 1 : -1 }[e.key];
    let next = step === undefined ? null : (index + step + homeCollections.length) % homeCollections.length;
    if (e.key === 'Home') next = 0;
    if (e.key === 'End') next = homeCollections.length - 1;
    if (next === null) return;
    e.preventDefault();
    setSelected(homeCollections[next].id);
    tabRefs.current[next]?.focus();
  };

  return (
    <section className="section essentials" aria-labelledby={`${uid}-title`}>
      <div className="container">
        <header className="section-head essentials__head">
          <h2 id={`${uid}-title`} className="essentials__title">{t('essentials.title')}</h2>
        </header>

        <div className="essentials__tabs-wrap">
          <div className="essentials__tabs" role="tablist" aria-label={t('essentials.tabsLabel')}>
            {homeCollections.map((c, i) => {
              const on = c.id === active.id;
              return (
                <button
                  key={c.id}
                  ref={(el) => { tabRefs.current[i] = el; }}
                  type="button"
                  role="tab"
                  id={tabId(c)}
                  aria-selected={on}
                  aria-controls={panelId}
                  tabIndex={on ? 0 : -1}
                  className={`essentials__tab ${on ? 'is-active' : ''}`}
                  onClick={() => setSelected(c.id)}
                  onKeyDown={(e) => onKeyDown(e, i)}
                >
                  {c.label}
                </button>
              );
            })}
          </div>
        </div>

        <div id={panelId} role="tabpanel" aria-labelledby={tabId(active)} className="essentials__panel">
          {items.length > 0 ? (
            <>
              <ul className="essentials__grid">
                {items.map((p) => <li key={p.id}><EssentialCard product={p} /></li>)}
              </ul>
              <p className="essentials__more">
                <Link
                  to={`/collections/${encodeURIComponent(active.id)}`}
                  className="essentials__view-all"
                  aria-label={t('essentials.viewAllNamed', { name: active.label })}
                >
                  {t('essentials.viewAll')} <ArrowRight size={17} aria-hidden="true" className="essentials__arrow" />
                </Link>
              </p>
            </>
          ) : (
            <div className="essentials__empty">
              <PackageOpen size={30} strokeWidth={1.5} aria-hidden="true" />
              <p className="essentials__empty-title">{t('essentials.emptyTitle')}</p>
              <p className="essentials__empty-text">{t('essentials.emptyText', { name: active.label })}</p>
              <Link to="/produits" className="btn btn--soft">{t('essentials.emptyCta')}</Link>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

/** Carte compacte : photo, nom, note (si avis approuvés), prix, stock, favori et ajout au panier existants. */
function EssentialCard({ product }) {
  const { favorites, toggleFavorite } = useCart();
  const quickAdd = useQuickAdd();
  const { t } = useI18n();
  const [added, setAdded] = useState(false);
  const timer = useRef();
  useEffect(() => () => clearTimeout(timer.current), []);

  const url = `/produits/${product.id}`;
  const name = product.displayName;
  const isFavorite = favorites.includes(product.id);
  const status = productStatus(product);
  const canBuy = status === 'available';
  const choice = hasChoice(product);
  const statusLabel = canBuy ? '' : t(`status.${status}`);
  // « À partir de » seulement si les variantes n'ont pas toutes le même prix.
  const prices = product.variants.map((v) => v.price).filter((v) => Number.isFinite(v));
  const from = prices.length > 1 && Math.min(...prices) !== Math.max(...prices) ? Math.min(...prices) : null;
  const { reviews } = product;

  const add = () => {
    if (quickAdd(product) === false) return;
    setAdded(true);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setAdded(false), 1400);
  };

  return (
    <article className="essential-card">
      <button
        type="button"
        className={`fav-btn ${isFavorite ? 'is-active' : ''}`}
        onClick={() => toggleFavorite(product.id)}
        aria-pressed={isFavorite}
        aria-label={isFavorite ? t('card.favRemove', { name }) : t('card.favAdd', { name })}
      >
        <Heart size={18} strokeWidth={1.6} />
      </button>
      <Link to={url} className="essential-card__media" tabIndex={-1} aria-hidden="true">
        <ProductImage image={product.cardImage} sizes="(min-width: 1000px) 280px, 46vw" />
      </Link>
      <div className="essential-card__body">
        <h3 className="essential-card__name"><Link to={url}>{name}</Link></h3>
        {reviews && (
          <p className="essential-card__rating">
            <Stars value={reviews.average} size={15} label={t('reviews.averageAria', { average: reviews.average })} />
            <span aria-hidden="true">{String(reviews.average).replace('.', ',')} ({reviews.count})</span>
            <span className="sr-only">{t('reviews.count', { count: reviews.count })}</span>
          </p>
        )}
        <p className="essential-card__price">
          {from !== null ? t('essentials.from', { price: formatPrice(from) }) : formatPrice(product.price)}
          {!canBuy && <span className="essential-card__stock">{statusLabel}</span>}
        </p>
        <button
          type="button"
          className={`btn btn--primary essential-card__add ${added ? 'is-added' : ''}`}
          onClick={add}
          disabled={!canBuy}
          aria-label={!canBuy ? t('card.statusNamed', { name, status: statusLabel })
            : choice ? t('card.chooseOptionOf', { name }) : t('card.addNamed', { name })}
        >
          {added ? <Check size={17} aria-hidden="true" /> : <ShoppingCart size={17} aria-hidden="true" />}
          <span>{added ? t('card.added') : !canBuy ? statusLabel : choice ? t('card.chooseOption') : t('common.addToCart')}</span>
        </button>
      </div>
    </article>
  );
}
