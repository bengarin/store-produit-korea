import { Link } from 'react-router-dom';
import { checkField } from './validate.js';

const LINK_FIELD = { type: 'link' };

/** Défilement fluide vers une ancre de la page (#collection), comme avant le thème. */
export function scrollToAnchor(e, hash) {
  const target = document.getElementById(hash.slice(1));
  if (!target) return;
  e.preventDefault();
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  target.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
  window.history.replaceState(window.history.state, '', hash);
}

/**
 * Lien issu du thème, revérifié à l'affichage : interne (/…), ancre (#…) ou https:// uniquement.
 * Un lien invalide ou vide devient un simple texte (jamais de javascript:, data:, etc.).
 */
export default function ThemeLink({ to, className, children, ...rest }) {
  const [value, error] = checkField(LINK_FIELD, to || '');
  if (!value || error) return <span className={className}>{children}</span>;
  if (value.startsWith('#')) {
    return <Link to={{ hash: value }} className={className} onClick={(e) => scrollToAnchor(e, value)} {...rest}>{children}</Link>;
  }
  if (value.startsWith('https://')) {
    return <a href={value} className={className} target="_blank" rel="noopener noreferrer" {...rest}>{children}</a>;
  }
  return <Link to={value} className={className} {...rest}>{children}</Link>;
}
