import { STORE_CONFIG } from '../config/store.js';
import { ORDERS_ARE_SIMULATED } from '../services/orderService.js';
import { Link } from 'react-router-dom';
import ThemeLink from '../theme/ThemeLink.jsx';
import { useTheme } from '../theme/ThemeContext.jsx';
import Logo from './Logo.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

/** Pied de page : logo, texte et liens du thème (facultatifs), puis la mention © toujours présente. */
export default function SiteFooter() {
  const { theme } = useTheme();
  const { t, tc } = useI18n();
  const { text } = theme.footer.settings;
  const links = theme.footer.items || [];
  return (
    <footer className="site-footer">
      <Logo variant="full" className="site-footer__logo" />
      {text && <p className="site-footer__text">{tc(text)}</p>}
      {links.length > 0 && (
        <nav className="site-footer__links" aria-label={t('footer.links')}>
          {links.map(({ label, link }, i) => <ThemeLink key={`${i}-${link}`} to={link}>{tc(label)}</ThemeLink>)}
        </nav>
      )}
      <p>© {new Date().getFullYear()} {STORE_CONFIG.brandName}{ORDERS_ARE_SIMULATED && t('demo.footer')}</p>
      <p className="site-footer__legal">
        <Link to="/confidentialite">{t('privacy.title')}</Link>
      </p>
    </footer>
  );
}
