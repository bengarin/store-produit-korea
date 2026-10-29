import { STORE_CONFIG } from '../config/store.js';
import Logo from './Logo.jsx';

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <Logo variant="full" className="site-footer__logo" />
      <p>© {new Date().getFullYear()} {STORE_CONFIG.brandName} — Boutique de démonstration. Les commandes sont simulées.</p>
    </footer>
  );
}
