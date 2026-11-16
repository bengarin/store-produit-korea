import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, ShoppingCart } from 'lucide-react';
import Logo from './Logo.jsx';
import MenuDrawer from './MenuDrawer.jsx';
import CategoriesMenu from './CategoriesMenu.jsx';
import HeaderSearch from './HeaderSearch.jsx';
import AnnouncementBar from './AnnouncementBar.jsx';
import { useCart } from '../context/CartContext.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { useTheme } from '../theme/ThemeContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';
import LanguageSwitcher from './LanguageSwitcher.jsx';

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

const CATALOG_LINK = '/produits';
const CART_LINK = '/panier';
// Pages ajoutées par la boutique elle-même (pas par le thème) : affichées après les liens du thème.
export const BLOG_LINK = '/blog';

export default function Header() {
  const { count } = useCart();
  const { theme } = useTheme();
  const { t, tc } = useI18n();
  const [menuOpen, setMenuOpen] = useState(false);
  const { pathname, search } = useLocation();
  // « Mon panier » n'apparaît pas en texte dans la barre : l'icône panier (à droite) y mène déjà.
  const links = theme.header.items.filter((l) => l.link !== CART_LINK);
  const { categoryTree } = useCatalog();
  const hasCategories = categoryTree.length > 0;
  const active = activeLink(links.map((l) => l.link), pathname, search);

  return (
    <>
      <AnnouncementBar />
      <header className="site-header">
        <div className="site-header__inner container">
          {/* Mobile : menu + loupe à gauche (logo centré) ; ordinateur : loupe à droite, avant la langue. */}
          <div className="site-header__start">
            <button className="icon-btn site-header__menu" onClick={() => setMenuOpen(true)} aria-label={t('header.openMenu')} aria-expanded={menuOpen}>
              <Menu size={22} strokeWidth={1.6} />
            </button>
            <HeaderSearch placement="start" />
          </div>
          <Logo />
          <nav className="site-nav" aria-label={t('header.mainNav')}>
            {links.map(({ label, link }, i) => (
              // Le lien du catalogue (« Nos produits ») devient le menu « Catégories » (Admin → Catégories).
              link === CATALOG_LINK && hasCategories
                ? <CategoriesMenu key={`${i}-${link}`} active={link === active} />
                : <Link key={`${i}-${link}`} to={link} aria-current={link === active ? 'page' : undefined} className={link === active ? 'active' : ''}>{tc(label)}</Link>
            ))}
            {!links.some((l) => l.link === BLOG_LINK) && (
              <Link to={BLOG_LINK} aria-current={pathname.startsWith(BLOG_LINK) ? 'page' : undefined} className={pathname.startsWith(BLOG_LINK) ? 'active' : ''}>
                {t('nav.blog')}
              </Link>
            )}
          </nav>
          <div className="site-header__actions">
            <HeaderSearch placement="end" />
            <LanguageSwitcher />
            <CartButton count={count} />
          </div>
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
  const { t } = useI18n();
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
    <Link to="/panier" className={`icon-btn cart-btn ${bump ? 'is-bumping' : ''}`} aria-label={t('header.cartAria', { count })}>
      <ShoppingCart size={22} strokeWidth={1.6} />
      {count > 0 && <span key={count} className="cart-btn__badge">{count > 99 ? '99+' : count}</span>}
    </Link>
  );
}
