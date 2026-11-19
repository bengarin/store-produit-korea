import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { BookOpen, Boxes, Layers, SlidersHorizontal, Star, ExternalLink, FolderTree, MessageSquareHeart, LayoutDashboard, LogOut, Menu, Package, Images, Palette, Settings, ShoppingBag, Users, X } from 'lucide-react';
import { useAuth } from '../auth.jsx';
import { can } from '../permissions.js';
import { ROLE_LABELS } from '../format.js';
import { useApi } from '../hooks.js';
import logo from '../../assets/brand/logo-jodhur-300.png';

const NAV = [
  { to: '/admin/dashboard', label: 'Tableau de bord', icon: LayoutDashboard, perm: 'viewDashboard' },
  { to: '/admin/orders', label: 'Commandes', icon: ShoppingBag, perm: 'viewOrders', badge: 'pending' },
  { to: '/admin/products', label: 'Produits', icon: Package, perm: 'viewProducts' },
  { to: '/admin/categories', label: 'Catégories', icon: FolderTree, perm: 'manageCategories' },
  { to: '/admin/collections', label: 'Collections', icon: Layers, perm: 'viewProducts' },
  { to: '/admin/filters', label: 'Filtres', icon: SlidersHorizontal, perm: 'manageFilters' },
  { to: '/admin/marketing', label: 'Visuels marketing', icon: Images, perm: 'viewProducts' },
  { to: '/admin/blog', label: 'Blog', icon: BookOpen, perm: 'viewBlog' },
  { to: '/admin/reviews', label: 'Avis clients', icon: MessageSquareHeart, perm: 'viewReviews', badge: 'reviews' },
  { to: '/admin/product-reviews', label: 'Avis produits', icon: Star, perm: 'viewReviews', badge: 'productReviews' },
  { to: '/admin/customers', label: 'Clients', icon: Users, perm: 'viewCustomers' },
  { to: '/admin/inventory', label: 'Stock', icon: Boxes, perm: 'viewInventory' },
  { to: '/admin/theme', label: 'Thème', icon: Palette, perm: 'viewTheme' },
  { to: '/admin/settings', label: 'Réglages', icon: Settings, perm: 'viewInventory' }, // mot de passe : tous les rôles
];

function Brand() {
  return (
    <div className="adm-brand">
      <img className="adm-brand__logo" src={logo} alt="Jodhur" width="300" height="75" decoding="async" />
      <span className="adm-brand__label">Administration</span>
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const pending = useApi('/orders', { status: 'pending', page_size: 1 }, { enabled: can(user, 'viewOrders') });
  // Avis clients en attente de validation (pastille dans le menu).
  const reviews = useApi('/reviews', { status: 'pending', page_size: 1 }, { enabled: can(user, 'moderateReviews') });
  const productReviews = useApi('/product-reviews', { status: 'pending', page_size: 1 }, { enabled: can(user, 'moderateReviews') });

  useEffect(() => setOpen(false), [location.pathname]);
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  const pendingCount = pending.data?.total || 0;
  const reviewsCount = reviews.data?.counts?.pending || 0;
  const productReviewsCount = productReviews.data?.counts?.pending || 0;

  return (
    <div className={`adm-shell ${open ? 'is-nav-open' : ''}`}>
      <header className="adm-topbar">
        <button type="button" className="adm-icon-btn" onClick={() => setOpen(true)} aria-label="Ouvrir le menu"
          aria-expanded={open} aria-controls="adm-sidebar">
          <Menu size={22} />
        </button>
        <Brand />
      </header>

      <aside id="adm-sidebar" className="adm-sidebar" aria-label="Navigation de l’administration">
        <div className="adm-sidebar__top">
          <Brand />
          <button type="button" className="adm-icon-btn adm-sidebar__close" onClick={() => setOpen(false)} aria-label="Fermer le menu">
            <X size={20} />
          </button>
        </div>
        <nav className="adm-nav">
          {NAV.filter((item) => can(user, item.perm)).map(({ to, label, icon: Icon, badge }) => (
            <NavLink key={to} to={to} className={({ isActive }) => `adm-nav__link ${isActive ? 'is-active' : ''}`}>
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
              {badge === 'pending' && pendingCount > 0 && (
                <span className="adm-nav__count" aria-label={`${pendingCount} en attente`}>{pendingCount}</span>
              )}
              {badge === 'reviews' && reviewsCount > 0 && (
                <span className="adm-nav__count" aria-label={`${reviewsCount} avis à valider`}>{reviewsCount}</span>
              )}
              {badge === 'productReviews' && productReviewsCount > 0 && (
                <span className="adm-nav__count" aria-label={`${productReviewsCount} avis produits à valider`}>{productReviewsCount}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="adm-sidebar__bottom">
          <a className="adm-nav__link" href="/" target="_blank" rel="noopener noreferrer">
            <ExternalLink size={18} aria-hidden="true" /><span>Voir la boutique</span>
          </a>
          <div className="adm-user">
            <span className="adm-user__avatar" aria-hidden="true">{(user.firstName || user.email)[0].toUpperCase()}</span>
            <div className="adm-user__text">
              <strong title={user.email}>{user.firstName ? `${user.firstName} ${user.lastName}`.trim() : user.email}</strong>
              <span>{ROLE_LABELS[user.role] || user.roleLabel}</span>
            </div>
            <button type="button" className="adm-icon-btn" onClick={logout} aria-label="Se déconnecter" title="Se déconnecter">
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>
      <button type="button" className="adm-scrim" aria-label="Fermer le menu" tabIndex={-1} onClick={() => setOpen(false)} />

      <main className="adm-main" id="adm-main">
        <Outlet context={{ refreshPending: pending.reload }} />
      </main>
    </div>
  );
}
