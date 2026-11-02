import { useEffect } from 'react';
import { PREVIEW, PREVIEW_MESSAGE, useTheme } from './ThemeContext.jsx';

/**
 * Aperçu de l'éditeur uniquement (rien n'est rendu pour les visiteurs) :
 * - bandeau « brouillon non publié » ;
 * - clic sur une section de l'accueil = sélection dans l'éditeur (les liens de la section ne s'ouvrent pas).
 */
export default function ThemePreviewBridge() {
  const { version } = useTheme();
  useEffect(() => {
    if (!PREVIEW || window.parent === window) return undefined;
    const onClick = (e) => {
      const el = e.target.closest?.('[data-theme-section]');
      if (!el) return;
      e.preventDefault();
      window.parent.postMessage({ type: `${PREVIEW_MESSAGE}:select`, id: el.dataset.themeSection }, window.location.origin);
    };
    document.addEventListener('click', onClick, true);
    return () => document.removeEventListener('click', onClick, true);
  }, []);
  // Visiteur avec « ?apercu-theme=1 » sans session de l'équipe : thème publié, aucun bandeau.
  if (!PREVIEW || version !== 'draft') return null;
  return <div className="theme-preview-badge" role="status">Aperçu du brouillon — non publié</div>;
}
