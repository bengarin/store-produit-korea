import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { NavLink } from 'react-router-dom';
import { X, Home, Store, Heart, ShoppingCart } from 'lucide-react';
import Logo from './Logo.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { ORDERS_ARE_SIMULATED } from '../services/orderService.js';
import { useCart } from '../context/CartContext.jsx';
import { useTheme } from '../theme/ThemeContext.jsx';

// Liens déjà présents dans le menu mobile (avec icône) ; les autres liens du thème sont ajoutés en dessous.
const BUILT_IN = new Set(['/', '/produits', '/produits?favoris=1', '/panier']);

export default function MenuDrawer({ open, onClose }) {
  const { count, favorites } = useCart();
  const { categories } = useCatalog();
  const { theme } = useTheme();
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
    <div className="drawer" role="dialog" aria-modal="true" aria-label="Menu">
      <button className="drawer__backdrop" onClick={onClose} aria-label="Fermer le menu" tabIndex={-1} />
      <nav className="drawer__panel">
        <div className="drawer__top">
          <Logo variant="full" />
          <button className="icon-btn" onClick={onClose} aria-label="Fermer le menu" autoFocus>
            <X size={22} />
          </button>
        </div>
        <ul className="drawer__links" onClick={onClose}>
          <li><NavLink to="/" end><Home size={18} /> Accueil</NavLink></li>
          <li><NavLink to="/produits" end><Store size={18} /> Nos produits</NavLink></li>
          {categories.map((c) => (
            <li key={c.id} className="drawer__sub">
              <NavLink to={`/produits?categorie=${c.id}`}>{c.label}</NavLink>
            </li>
          ))}
          {extra.map(({ label, link }, i) => (
            <li key={`${i}-${link}`}><NavLink to={link}>{label}</NavLink></li>
          ))}
          <li><NavLink to="/produits?favoris=1"><Heart size={18} /> Mes favoris ({favorites.length})</NavLink></li>
          <li><NavLink to="/panier"><ShoppingCart size={18} /> Mon panier ({count})</NavLink></li>
        </ul>
        {ORDERS_ARE_SIMULATED && <p className="drawer__note">Boutique de démonstration — les commandes sont simulées.</p>}
      </nav>
    </div>,
    document.body,
  );
}
