import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { NavLink } from 'react-router-dom';
import { X, Home, Store, Heart, ShoppingCart } from 'lucide-react';
import Logo from './Logo.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { ORDERS_ARE_SIMULATED } from '../services/orderService.js';
import { useCart } from '../context/CartContext.jsx';
import { useTheme } from '../theme/ThemeContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';
import LanguageSwitcher from './LanguageSwitcher.jsx';

// Liens déjà présents dans le menu mobile (avec icône) ; les autres liens du thème sont ajoutés en dessous.
const BUILT_IN = new Set(['/', '/produits', '/produits?favoris=1', '/panier']);

export default function MenuDrawer({ open, onClose }) {
  const { count, favorites } = useCart();
  const { categories } = useCatalog();
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
          <li><NavLink to="/produits" end><Store size={18} /> {t('nav.products')}</NavLink></li>
          {categories.map((c) => (
            <li key={c.id} className="drawer__sub">
              <NavLink to={`/produits?categorie=${c.id}`}>{tc(c.label)}</NavLink>
            </li>
          ))}
          {extra.map(({ label, link }, i) => (
            <li key={`${i}-${link}`}><NavLink to={link}>{tc(label)}</NavLink></li>
          ))}
          <li><NavLink to="/produits?favoris=1"><Heart size={18} /> {t('nav.favorites', { count: favorites.length })}</NavLink></li>
          <li><NavLink to="/panier"><ShoppingCart size={18} /> {t('nav.cart', { count })}</NavLink></li>
        </ul>
        <LanguageSwitcher full className="drawer__lang" />
        {ORDERS_ARE_SIMULATED && <p className="drawer__note">{t('demo.drawer')}</p>}
      </nav>
    </div>,
    document.body,
  );
}
