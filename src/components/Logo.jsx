import { Link } from 'react-router-dom';
import { STORE_CONFIG } from '../config/store.js';
import logoFull from '../assets/brand/logo-full.webp';
import logoCompact from '../assets/brand/logo-compact.webp';

/**
 * Logo Ma Petite Corée.ma — recadrages du fichier fourni (design/brand/logo-mapetitecoree-original.webp, hors bundle).
 * - variant "compact" : symbole + nom sur deux lignes (header)
 * - variant "full"    : symbole + nom + « KOREAN & NATURAL SKINCARE » (menu, footer)
 */
export default function Logo({ variant = 'compact', link = true, className = '' }) {
  const full = variant === 'full';
  const img = (
    <img
      className="logo__img"
      src={full ? logoFull : logoCompact}
      width={full ? 700 : 560}
      height={full ? 476 : 400}
      alt={`${STORE_CONFIG.brandName} — Korean & Natural Skincare`}
      decoding="async"
    />
  );
  if (!link) return <span className={`logo logo--${variant} ${className}`}>{img}</span>;
  return (
    <Link to="/" className={`logo logo--${variant} ${className}`} aria-label={`${STORE_CONFIG.brandName} — accueil`}>
      {img}
    </Link>
  );
}
