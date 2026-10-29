import { STORE_CONFIG } from '../config/store.js';

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <p>© {new Date().getFullYear()} {STORE_CONFIG.brandName} — Boutique de démonstration. Les commandes sont simulées.</p>
    </footer>
  );
}
