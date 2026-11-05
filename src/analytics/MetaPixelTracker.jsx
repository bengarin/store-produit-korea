import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { ensurePixel, track, trackingAvailable, trackingDisabledReason } from './metaPixel.js';

// Développement uniquement : explique dans la console pourquoi Meta Pixel Helper ne voit aucun pixel.
if (import.meta.env.DEV) {
  if (trackingDisabledReason) console.info(`[Meta Pixel] inactif : ${trackingDisabledReason}.`);
}

// Navigation déjà comptée (au niveau du module : le double appel des effets en mode strict ne la recompte pas).
let lastPageKey = null;

const CONTACT_LINK = /^(https:\/\/(wa\.me|api\.whatsapp\.com)\/|tel:|mailto:)/i;
const contactChannel = (href) => (href.startsWith('tel:') ? 'phone' : href.startsWith('mailto:') ? 'email' : 'whatsapp');

/**
 * Boutique publique uniquement : un PageView par navigation réelle,
 * événement Contact sur les liens WhatsApp / téléphone / e-mail.
 */
export default function MetaPixelTracker() {
  const location = useLocation();
  // PageView : une fois par entrée d'historique (location.key).
  useEffect(() => {
    if (!trackingAvailable) return;
    const pageKey = location.key;
    if (pageKey === lastPageKey) return;
    if (!ensurePixel()) return;
    lastPageKey = pageKey;
    track('PageView');
  }, [location.key]);

  // Contact : clic sur un lien de contact (délégation, aucun composant à modifier).
  useEffect(() => {
    if (!trackingAvailable) return undefined;
    const onClick = (e) => {
      const href = e.target.closest?.('a[href]')?.getAttribute('href') || '';
      if (CONTACT_LINK.test(href)) track('Contact', { content_name: contactChannel(href) });
    };
    document.addEventListener('click', onClick, true);
    return () => document.removeEventListener('click', onClick, true);
  }, []);

  return null;
}
