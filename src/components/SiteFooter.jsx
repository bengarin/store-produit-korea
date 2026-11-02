import { STORE_CONFIG } from '../config/store.js';
import { ORDERS_ARE_SIMULATED } from '../services/orderService.js';
import ThemeLink from '../theme/ThemeLink.jsx';
import { useTheme } from '../theme/ThemeContext.jsx';
import Logo from './Logo.jsx';

/** Pied de page : logo, texte et liens du thème (facultatifs), puis la mention © toujours présente. */
export default function SiteFooter() {
  const { theme } = useTheme();
  const { text } = theme.footer.settings;
  const links = theme.footer.items || [];
  return (
    <footer className="site-footer">
      <Logo variant="full" className="site-footer__logo" />
      {text && <p className="site-footer__text">{text}</p>}
      {links.length > 0 && (
        <nav className="site-footer__links" aria-label="Liens du pied de page">
          {links.map(({ label, link }, i) => <ThemeLink key={`${i}-${link}`} to={link}>{label}</ThemeLink>)}
        </nav>
      )}
      <p>© {new Date().getFullYear()} {STORE_CONFIG.brandName}{ORDERS_ARE_SIMULATED && ' — Boutique de démonstration. Les commandes sont simulées.'}</p>
    </footer>
  );
}
