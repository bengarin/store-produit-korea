import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, ShoppingCart } from 'lucide-react';
import Logo from './Logo.jsx';
import MenuDrawer from './MenuDrawer.jsx';
import AnnouncementBar from './AnnouncementBar.jsx';
import { useCart } from '../context/CartContext.jsx';
import { useTheme } from '../theme/ThemeContext.jsx';

/**
 * Lien actif : même chemin (ou sous-page) et mêmes paramètres ; « / » seulement exact. Un lien sans paramètre n'est pas actif
 * si un autre lien du menu, plus précis, correspond (ex. « Nos produits » vs « Favoris »).
 */
function activeLink(links, pathname, search) {
  const current = new URLSearchParams(search);
  const matches = links.filter((link) => {
    const [path, query = ''] = link.split('?');
    // Sans paramètre, un lien est aussi actif sur ses sous-pages (« Nos produits » sur une fiche produit).
    const samePage = path === pathname || (!query && path !== '/' && pathname.startsWith(`${path}/`));
    if (!samePage) return false;
    return [...new URLSearchParams(query)].every(([k, v]) => current.get(k) === v);
  });
  return matches.sort((a, b) => b.length - a.length)[0];
}

export default function Header() {
  const { count } = useCart();
  const { theme } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);
  const { pathname, search } = useLocation();
  const links = theme.header.items;
  const active = activeLink(links.map((l) => l.link), pathname, search);

  return (
    <>
      <AnnouncementBar />
      <header className="site-header">
        <div className="site-header__inner container">
          <button className="icon-btn site-header__menu" onClick={() => setMenuOpen(true)} aria-label="Ouvrir le menu" aria-expanded={menuOpen}>
            <Menu size={22} strokeWidth={1.6} />
          </button>
          <Logo />
          <nav className="site-nav" aria-label="Navigation principale">
            {links.map(({ label, link }, i) => (
              <Link key={`${i}-${link}`} to={link} aria-current={link === active ? 'page' : undefined} className={link === active ? 'active' : ''}>{label}</Link>
            ))}
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
  // Petit rebond de l'icône à chaque ajout (le compteur augmente).
  const prev = useRef(count);
  const [bump, setBump] = useState(false);
  useEffect(() => {
    if (count > prev.current) {
      setBump(true);
      const t = setTimeout(() => setBump(false), 600);
      prev.current = count;
      return () => clearTimeout(t);
    }
    prev.current = count;
    return undefined;
  }, [count]);

  return (
    <Link to="/panier" className={`icon-btn cart-btn ${bump ? 'is-bumping' : ''}`} aria-label={`Mon panier, ${count} article${count > 1 ? 's' : ''}`}>
      <ShoppingCart size={22} strokeWidth={1.6} />
      {count > 0 && <span key={count} className="cart-btn__badge">{count > 99 ? '99+' : count}</span>}
    </Link>
  );
}
