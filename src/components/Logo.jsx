import { Link } from 'react-router-dom';
import { STORE_CONFIG } from '../config/store.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import logo400 from '../assets/brand/logo-jodhur-400.png';
import logo300 from '../assets/brand/logo-jodhur-300.png';

/**
 * Logo Jodhur — fichiers fournis (design/brand/Logo-JODHUR-400x100px.png et 300x75px.png), fond transparent.
 * Proportions d'origine (4:1) : la hauteur est fixée en CSS, la largeur suit (jamais déformé).
 * - variant "compact" : en-tête
 * - variant "full"    : menu et pied de page (un peu plus grand)
 * Le navigateur choisit la version 300 px ou 400 px selon la taille affichée et la netteté de l'écran.
 */
const SIZES = {
  compact: '(min-width: 1000px) 192px, 152px',
  full: '(min-width: 1000px) 256px, 224px',
};

export default function Logo({ variant = 'compact', link = true, className = '' }) {
  const { t } = useI18n();
  const img = (
    <img
      className="logo__img"
      src={logo400}
      srcSet={`${logo300} 300w, ${logo400} 400w`}
      sizes={SIZES[variant] || SIZES.compact}
      width={400}
      height={100}
      alt={STORE_CONFIG.brandName}
      decoding="async"
    />
  );
  if (!link) return <span className={`logo logo--${variant} ${className}`}>{img}</span>;
  return (
    <Link to="/" className={`logo logo--${variant} ${className}`} aria-label={t('logo.home', { brand: STORE_CONFIG.brandName })}>
      {img}
    </Link>
  );
}
