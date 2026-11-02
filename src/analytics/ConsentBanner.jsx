import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { getConsent, onConsentChange, setConsent } from './consent.js';
import { Link } from 'react-router-dom';
import { useI18n } from '../i18n/I18nContext.jsx';

/**
 * Bandeau affiché tant que le visiteur n'a pas choisi (ou s'il rouvre ses préférences). Refuser = aussi simple qu'accepter.
 * Tant qu'il est ouvert, la page réserve sa hauteur en bas : aucun bouton (ex. « Confirmer la commande ») ne reste caché dessous.
 */
export default function ConsentBanner() {
  const { t } = useI18n();
  const [open, setOpen] = useState(() => getConsent() === null);
  const ref = useRef(null);

  useEffect(() => onConsentChange(({ open: reopen }) => setOpen(Boolean(reopen))), []);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!open || !el) return undefined;
    const reserve = () => { document.body.style.paddingBottom = `${Math.ceil(el.getBoundingClientRect().height) + 24}px`; };
    reserve();
    const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(reserve) : null;
    observer?.observe(el);
    return () => {
      observer?.disconnect();
      document.body.style.paddingBottom = '';
    };
  }, [open]);

  if (!open) return null;
  return (
    <section ref={ref} className="consent" role="dialog" aria-modal="false" aria-labelledby="consent-title" aria-describedby="consent-text">
      <p className="consent__title" id="consent-title">{t('consent.label')}</p>
      <p id="consent-text">{t('consent.text')} <Link to="/confidentialite" className="consent__more">{t('consent.more')}</Link></p>
      <div className="consent__actions">
        <button type="button" className="btn btn--soft" onClick={() => setConsent('denied')}>{t('consent.refuse')}</button>
        <button type="button" className="btn btn--primary" onClick={() => setConsent('granted')}>{t('consent.accept')}</button>
      </div>
    </section>
  );
}
