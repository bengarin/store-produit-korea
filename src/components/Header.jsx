import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Menu, ShoppingCart } from 'lucide-react';
import Logo from './Logo.jsx';
import MenuDrawer from './MenuDrawer.jsx';
import { useCart } from '../context/CartContext.jsx';

export default function Header() {
  const { count } = useCart();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="site-header">
      <div className="site-header__inner container">
        <button className="icon-btn" onClick={() => setMenuOpen(true)} aria-label="Ouvrir le menu" aria-expanded={menuOpen}>
          <Menu size={24} strokeWidth={1.6} />
        </button>
        <Logo />
        <CartButton count={count} />
      </div>
      <MenuDrawer open={menuOpen} onClose={() => setMenuOpen(false)} />
    </header>
  );
}

export function CartButton({ count }) {
  return (
    <Link to="/panier" className="icon-btn cart-btn" aria-label={`Mon panier, ${count} article${count > 1 ? 's' : ''}`}>
      <ShoppingCart size={24} strokeWidth={1.6} />
      {count > 0 && <span className="cart-btn__badge">{count > 99 ? '99+' : count}</span>}
    </Link>
  );
}
