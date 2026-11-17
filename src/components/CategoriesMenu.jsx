import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link, useLocation } from 'react-router-dom';
import { ArrowRight, ChevronDown } from 'lucide-react';
import ProductImage from './ProductImage.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

const CLOSE_DELAY = 180; // ms : laisse le temps de passer du bouton au panneau sans fermer le menu
const canHover = () => typeof window !== 'undefined' && window.matchMedia?.('(hover: hover) and (pointer: fine)').matches;

/**
 * Menu déroulant de la barre de navigation (ordinateur) : bouton + panneau pleine largeur sous la barre.
 * Ouverture au survol (souris) ou au clic ; fermeture après un choix, au clic en dehors, avec Échap,
 * en quittant le menu à la souris (s'il a été ouvert au survol) ou au changement de page.
 * `children(close)` : contenu du panneau.
 */
function NavDropdown({ label, active = false, children }) {
  const [open, setOpen] = useState(false);
  const pinned = useRef(false); // ouvert au clic : ne se ferme pas en quittant à la souris
  const timer = useRef(null);
  const triggerRef = useRef(null);
  const panelRef = useRef(null);
  const panelId = useId();
  const { pathname, search } = useLocation();

  const close = useCallback(() => {
    clearTimeout(timer.current);
    pinned.current = false;
    setOpen(false);
  }, []);

  // Changement de page (choix d'un lien, retour arrière…) : le menu se ferme.
  useEffect(() => close(), [pathname, search, close]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key !== 'Escape') return;
      close();
      triggerRef.current?.focus();
    };
    // Clic (ou toucher) en dehors du bouton et du panneau : fermeture.
    const onDown = (e) => {
      if (triggerRef.current?.contains(e.target) || panelRef.current?.contains(e.target)) return;
      close();
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onDown);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onDown);
    };
  }, [open, close]);

  useEffect(() => () => clearTimeout(timer.current), []);

  const hoverOpen = () => {
    if (!canHover()) return;
    clearTimeout(timer.current);
    setOpen(true);
  };
  const hoverClose = () => {
    if (!canHover() || pinned.current) return;
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setOpen(false), CLOSE_DELAY);
  };
  const toggle = () => {
    clearTimeout(timer.current);
    if (open && pinned.current) return close();
    pinned.current = true;
    return setOpen(true);
  };

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className={`site-nav__trigger ${open || active ? 'active' : ''} ${open ? 'is-open' : ''}`}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={toggle}
        onMouseEnter={hoverOpen}
        onMouseLeave={hoverClose}
      >
        {label}
        <ChevronDown size={15} strokeWidth={1.8} aria-hidden="true" className="site-nav__chevron" />
      </button>
      <div
        ref={panelRef}
        id={panelId}
        className={`mega-menu ${open ? 'is-open' : ''}`}
        hidden={!open}
        onMouseEnter={hoverOpen}
        onMouseLeave={hoverClose}
      >
        <div className="mega-menu__inner container">{children(close)}</div>
      </div>
      {/* Voile sur la page (rendu hors du <header> : son flou d'arrière-plan enfermerait un élément « fixed »). */}
      {open && createPortal(<div className="mega-menu__veil" aria-hidden="true" />, document.body)}
    </>
  );
}

/** « Catégories » : catégories et sous-catégories gérées dans Admin → Catégories. */
export default function CategoriesMenu({ active = false }) {
  const { categoryTree } = useCatalog();
  const { t, tc } = useI18n();
  if (!categoryTree.length) return null;
  return (
    <NavDropdown label={t('nav.categories')} active={active}>
      {(close) => categoryTree.map((cat) => (
        <div key={cat.id} className="mega-menu__col">
          <Link to={`/produits?categorie=${encodeURIComponent(cat.id)}`} className="mega-menu__title" onClick={close}>
            {tc(cat.label)}
          </Link>
          {cat.children.length > 0 && (
            <ul className="mega-menu__list">
              {cat.children.map((sub) => (
                <li key={sub.id}>
                  <Link to={`/produits?categorie=${encodeURIComponent(sub.id)}`} onClick={close}>{tc(sub.label)}</Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </NavDropdown>
  );
}

/** « Boutique » : tous les produits + les collections (Admin → Collections), avec image et description. */
export function ShopMenu({ active = false }) {
  const { collections } = useCatalog();
  const { t } = useI18n();
  if (!collections.length) return null;
  return (
    <NavDropdown label={t('nav.shop')} active={active}>
      {(close) => (
        <div className="shop-menu">
          <div className="shop-menu__intro">
            <p className="mega-menu__title">{t('collections.title')}</p>
            <p className="shop-menu__text">{t('collections.menuIntro')}</p>
            <Link to="/produits" className="shop-menu__all" onClick={close}>
              {t('nav.allProducts')} <ArrowRight size={16} aria-hidden="true" className="shop-menu__arrow" />
            </Link>
          </div>
          <ul className="shop-menu__list">
            {collections.map((c) => (
              <li key={c.id}>
                <Link to={`/collections/${encodeURIComponent(c.id)}`} className="shop-menu__card" onClick={close}>
                  {c.image && <ProductImage image={c.image} sizes="160px" className="shop-menu__img" />}
                  <span className="shop-menu__name">{c.label}</span>
                  {c.description && <span className="shop-menu__desc">{c.description}</span>}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </NavDropdown>
  );
}
