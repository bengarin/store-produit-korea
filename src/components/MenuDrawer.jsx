import { useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { X, Home, Store, Heart, ShoppingCart } from 'lucide-react';
import Logo from './Logo.jsx';
import { CATEGORIES } from '../data/products.js';
import { useCart } from '../context/CartContext.jsx';

export default function MenuDrawer({ open, onClose }) {
  const { count, favorites } = useCart();

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

  return (
    <div className="drawer" role="dialog" aria-modal="true" aria-label="Menu">
      <button className="drawer__backdrop" onClick={onClose} aria-label="Fermer le menu" tabIndex={-1} />
      <nav className="drawer__panel">
        <div className="drawer__top">
          <Logo compact />
          <button className="icon-btn" onClick={onClose} aria-label="Fermer le menu" autoFocus>
            <X size={22} />
          </button>
        </div>
        <ul className="drawer__links" onClick={onClose}>
          <li><NavLink to="/" end><Home size={18} /> Accueil</NavLink></li>
          <li><NavLink to="/produits" end><Store size={18} /> Nos produits</NavLink></li>
          {CATEGORIES.filter((c) => c.id !== 'all').map((c) => (
            <li key={c.id} className="drawer__sub">
              <NavLink to={`/produits?categorie=${c.id}`}>{c.label}</NavLink>
            </li>
          ))}
          <li><NavLink to="/produits?favoris=1"><Heart size={18} /> Mes favoris ({favorites.length})</NavLink></li>
          <li><NavLink to="/panier"><ShoppingCart size={18} /> Mon panier ({count})</NavLink></li>
        </ul>
        <p className="drawer__note">Boutique de démonstration — les commandes sont simulées.</p>
      </nav>
    </div>
  );
}
