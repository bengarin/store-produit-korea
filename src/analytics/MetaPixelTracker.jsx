import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { getConsent, onConsentChange, trackingAvailable } from './consent.js';
import { ensurePixel, revokePixel, track } from './metaPixel.js';
import ConsentBanner from './ConsentBanner.jsx';

// Navigation déjà comptée (au niveau du module : le double appel des effets en mode strict ne la recompte pas).
let lastPageKey = null;

const CONTACT_LINK = /^(https:\/\/(wa\.me|api\.whatsapp\.com)\/|tel:|mailto:)/i;
const contactChannel = (href) => (href.startsWith('tel:') ? 'phone' : href.startsWith('mailto:') ? 'email' : 'whatsapp');

/**
 * Boutique publique uniquement : bandeau de consentement, un PageView par navigation réelle,
 * événement Contact sur les liens WhatsApp / téléphone / e-mail.
 */
export default function MetaPixelTracker() {
  const location = useLocation();
  const [consent, setConsentState] = useState(getConsent);

  useEffect(() => onConsentChange(({ consent: value }) => {
    setConsentState(value);
    if (value === 'denied') revokePixel();
  }), []);

  // PageView : une fois par entrée d'historique (location.key), y compris la première page après consentement.
  useEffect(() => {
    if (!trackingAvailable || consent !== 'granted') return;
    const pageKey = location.key;
    if (pageKey === lastPageKey) return;
    if (!ensurePixel()) return;
    lastPageKey = pageKey;
    track('PageView');
  }, [location.key, consent]);

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

  if (!trackingAvailable) return null;
  return <ConsentBanner />;
}
