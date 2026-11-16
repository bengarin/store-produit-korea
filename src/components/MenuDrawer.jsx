import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link, NavLink } from 'react-router-dom';
import { X, Home, Store, Heart, ShoppingCart, ChevronDown, BookOpen, Star } from 'lucide-react';
import Logo from './Logo.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { ORDERS_ARE_SIMULATED } from '../services/orderService.js';
import { useCart } from '../context/CartContext.jsx';
import { useTheme } from '../theme/ThemeContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';
import LanguageSwitcher from './LanguageSwitcher.jsx';

// Liens déjà présents dans le menu mobile (avec icône) ; les autres liens du thème sont ajoutés en dessous.
const BUILT_IN = new Set(['/', '/produits', '/produits?favoris=1', '/panier', '/blog', '/avis']);

export default function MenuDrawer({ open, onClose }) {
  const { count, favorites } = useCart();
  const { categoryTree } = useCatalog();
  const { theme } = useTheme();
  const { t, tc } = useI18n();
  const extra = theme.header.items.filter((l) => !BUILT_IN.has(l.link));

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="drawer" role="dialog" aria-modal="true" aria-label={t('menu.label')}>
      <button className="drawer__backdrop" onClick={onClose} aria-label={t('menu.close')} tabIndex={-1} />
      <nav className="drawer__panel">
        <div className="drawer__top">
          <Logo variant="full" />
          <button className="icon-btn" onClick={onClose} aria-label={t('menu.close')} autoFocus>
            <X size={22} />
          </button>
        </div>
        <ul className="drawer__links" onClick={onClose}>
          <li><NavLink to="/" end><Home size={18} /> {t('nav.home')}</NavLink></li>
          {categoryTree.length ? (
            <CategoryAccordion tree={categoryTree} />
          ) : (
            <li><NavLink to="/produits" end><Store size={18} /> {t('nav.products')}</NavLink></li>
          )}
          {extra.map(({ label, link }, i) => (
            <li key={`${i}-${link}`}><NavLink to={link}>{tc(label)}</NavLink></li>
          ))}
          <li><NavLink to="/produits?favoris=1"><Heart size={18} /> {t('nav.favorites', { count: favorites.length })}</NavLink></li>
          <li><NavLink to="/panier"><ShoppingCart size={18} /> {t('nav.cart', { count })}</NavLink></li>
          <li><NavLink to="/blog"><BookOpen size={18} /> {t('nav.blog')}</NavLink></li>
          <li><NavLink to="/avis"><Star size={18} /> {t('nav.reviews')}</NavLink></li>
        </ul>
        <LanguageSwitcher full className="drawer__lang" />
        {ORDERS_ARE_SIMULATED && <p className="drawer__note">{t('demo.drawer')}</p>}
      </nav>
    </div>,
    document.body,
  );
}

/**
 * « Catégories » (mobile) : s'ouvre au toucher ; chaque catégorie mène à ses produits, la flèche affiche
 * ses sous-catégories. Les boutons n'ont pas d'effet sur la fermeture du menu (seuls les liens le ferment).
 */
function CategoryAccordion({ tree }) {
  const { t, tc } = useI18n();
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(null);
  const keep = (fn) => (e) => {
    e.stopPropagation();
    fn();
  };
  return (
    <li className="drawer__group">
      <button type="button" className={`drawer__toggle ${open ? 'is-open' : ''}`} aria-expanded={open}
        onClick={keep(() => setOpen((v) => !v))}>
        <Store size={18} /> <span>{t('nav.categories')}</span>
        <ChevronDown size={18} aria-hidden="true" className="drawer__chevron" />
      </button>
      {open && (
        <ul className="drawer__cats">
          <li><Link to="/produits" end>{t('nav.allProducts')}</Link></li>
          {tree.map((cat) => {
            const isOpen = expanded === cat.id;
            const label = tc(cat.label);
            return (
              <li key={cat.id} className="drawer__cat">
                <div className="drawer__cat-row">
                  <Link to={`/produits?categorie=${encodeURIComponent(cat.id)}`}>{label}</Link>
                  {cat.children.length > 0 && (
                    <button type="button" className={`drawer__cat-toggle ${isOpen ? 'is-open' : ''}`} aria-expanded={isOpen}
                      aria-label={t('nav.toggleSub', { label })} onClick={keep(() => setExpanded(isOpen ? null : cat.id))}>
                      <ChevronDown size={18} aria-hidden="true" />
                    </button>
                  )}
                </div>
                {isOpen && (
                  <ul className="drawer__subs">
                    {cat.children.map((sub) => (
                      <li key={sub.id}><Link to={`/produits?categorie=${encodeURIComponent(sub.id)}`}>{tc(sub.label)}</Link></li>
                    ))}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </li>
  );
}
