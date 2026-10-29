import { Link } from 'react-router-dom';
import { STORE_CONFIG } from '../config/store.js';

export default function Logo({ compact = false }) {
  return (
    <Link to="/" className={`logo ${compact ? 'logo--compact' : ''}`} aria-label={`${STORE_CONFIG.brandName} — accueil`}>
      <svg className="logo__mark" viewBox="0 0 40 32" aria-hidden="true">
        <path d="M20 30 C 20 22 20 14 20 6" />
        <path d="M20 30 C 12 28 7 22 7 14 C 14 15 19 21 20 30 Z" />
        <path d="M20 30 C 28 28 33 22 33 14 C 26 15 21 21 20 30 Z" />
        <path d="M20 22 C 15 18 14 10 20 2 C 26 10 25 18 20 22 Z" />
      </svg>
      <span className="logo__text">
        <span className="logo__name">{STORE_CONFIG.brandName}</span>
        {!compact && <span className="logo__tagline">{STORE_CONFIG.brandTagline}</span>}
      </span>
    </Link>
  );
}
