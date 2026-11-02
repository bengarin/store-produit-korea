import { useState } from 'react';
import { Mail } from 'lucide-react';
import Reveal from './Reveal.jsx';
import { DATA_SOURCE } from '../config/env.js';
import { api } from '../api/client.js';
import { ENDPOINTS } from '../api/endpoints.js';
import { useI18n } from '../i18n/I18nContext.jsx';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/**
 * Newsletter (section « newsletter ») : inscription réelle enregistrée par le serveur, avec consentement
 * explicite (case à cocher). Mode démo : rien n'est envoyé, un message le dit clairement.
 */
export default function NewsletterSection({ section }) {
  const { t, tc, lang } = useI18n();
  // Le texte de consentement enregistré par le serveur est celui réellement affiché (dans la langue de la page).
  const [heading, text, buttonLabel, consentText] = ['heading', 'text', 'buttonLabel', 'consentText'].map((k) => tc(section.settings[k]));
  const [email, setEmail] = useState('');
  const [consent, setConsent] = useState(false);
  const [website, setWebsite] = useState(''); // champ piège invisible (anti-robots)
  const [state, setState] = useState({ status: 'idle', message: '' });
  const titleId = `${section.id}-title`;
  const idBase = `nl-${section.id}`;

  const submit = async (e) => {
    e.preventDefault();
    if (!EMAIL_RE.test(email.trim())) return setState({ status: 'error', message: t('newsletter.invalidEmail') });
    if (!consent) return setState({ status: 'error', message: t('newsletter.consentRequired') });
    if (DATA_SOURCE === 'local') {
      return setState({ status: 'done', message: t('newsletter.demo') });
    }
    setState({ status: 'sending', message: '' });
    try {
      await api.post(ENDPOINTS.newsletter, { email: email.trim(), consent: true, consentText, website });
      setState({ status: 'done', message: t('newsletter.done') });
    } catch (err) {
      // Message du serveur (en français) affiché seulement en français ; sinon message traduit.
      const fieldMessage = lang === 'fr' ? err?.data?.error?.fields?.email?.[0] : null;
      setState({ status: 'error', message: fieldMessage || t('newsletter.error') });
    }
  };

  return (
    <section className="home-section newsletter" aria-labelledby={titleId}>
      <Reveal className="container">
        <div className="newsletter__box">
          <Mail size={26} strokeWidth={1.4} className="newsletter__icon" aria-hidden="true" />
          <h2 className="newsletter__title" id={titleId}>{heading}</h2>
          {text && <p className="newsletter__text">{text}</p>}
          {state.status === 'done' ? (
            <p className="newsletter__done" role="status">{state.message}</p>
          ) : (
            <form className="newsletter__form" onSubmit={submit} noValidate>
              <div className="newsletter__row">
                <label htmlFor={`${idBase}-email`} className="sr-only">{t('newsletter.emailLabel')}</label>
                <input id={`${idBase}-email`} type="email" autoComplete="email" placeholder={t('newsletter.emailPlaceholder')} value={email}
                  onChange={(e) => setEmail(e.target.value)} maxLength={254} aria-invalid={state.status === 'error'} />
                <button type="submit" className="btn btn--primary" disabled={state.status === 'sending'}>{buttonLabel}</button>
              </div>
              <label className="newsletter__consent">
                <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
                <span>{consentText}</span>
              </label>
              <div className="hp-field" aria-hidden="true">
                <label htmlFor={`${idBase}-website`}>{t('common.honeypot')}</label>
                <input id={`${idBase}-website`} tabIndex={-1} autoComplete="off" value={website} onChange={(e) => setWebsite(e.target.value)} />
              </div>
              {state.status === 'error' && <p className="field__error" role="alert">{state.message}</p>}
            </form>
          )}
        </div>
      </Reveal>
    </section>
  );
}
