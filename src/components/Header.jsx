import { useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { Menu, ShoppingCart } from 'lucide-react';
import Logo from './Logo.jsx';
import MenuDrawer from './MenuDrawer.jsx';
import { useCart } from '../context/CartContext.jsx';

export default function Header() {
  const { count } = useCart();
  const [menuOpen, setMenuOpen] = useState(false);
  const { pathname, search } = useLocation();
  const onFavorites = pathname === '/produits' && search.includes('favoris=1');

  return (
    <>
      <header className="site-header">
        <div className="site-header__inner container">
          <button className="icon-btn site-header__menu" onClick={() => setMenuOpen(true)} aria-label="Ouvrir le menu" aria-expanded={menuOpen}>
            <Menu size={22} strokeWidth={1.6} />
          </button>
          <Logo />
          <nav className="site-nav" aria-label="Navigation principale">
            <NavLink to="/" end>Accueil</NavLink>
            <NavLink to="/produits" className={({ isActive }) => (isActive && !onFavorites ? 'active' : '')}>Nos produits</NavLink>
            <Link to="/produits?favoris=1" className={onFavorites ? 'active' : ''}>Favoris</Link>
            <Link to="/panier">Mon panier</Link>
          </nav>
          <CartButton count={count} />
        </div>
      </header>
      {/* Rendu hors du <header> : son flou d'arrière-plan enfermait le menu. */}
      <MenuDrawer open={menuOpen} onClose={() => setMenuOpen(false)} />
    </>
  );
}

export function CartButton({ count }) {
  return (
    <Link to="/panier" className="icon-btn cart-btn" aria-label={`Mon panier, ${count} article${count > 1 ? 's' : ''}`}>
      <ShoppingCart size={22} strokeWidth={1.6} />
      {count > 0 && <span className="cart-btn__badge">{count > 99 ? '99+' : count}</span>}
    </Link>
  );
}
