import { Info } from 'lucide-react';
import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import { useCatalog } from '../context/CatalogContext.jsx';
import { STORE_CONFIG } from '../config/store.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { PRIVACY_UPDATED, privacySections } from '../i18n/privacy.js';
import { openConsentSettings, trackingAvailable } from '../analytics/consent.js';

const URL_RE = /(https:\/\/[^\s]+|www\.[^\s]+)/;

/** Adresses web : liens cliquables, toujours lus de gauche à droite (même dans une page en arabe). */
function WithLinks({ text }) {
  return text.split(URL_RE).map((part, i) => (i % 2 === 1
    ? <a key={i} href={part.startsWith('http') ? part : `https://${part}`} dir="ltr" target="_blank" rel="noopener noreferrer">{part}</a>
    : part));
}

/** Politique de confidentialité (français / arabe). Texte d'information, non validé juridiquement. */
export default function PrivacyPage() {
  const { t, lang } = useI18n();
  const { config } = useCatalog();
  const legal = config.legal || {};
  const sections = privacySections(lang, {
    brand: config.brandName || STORE_CONFIG.brandName,
    name: legal.name,
    address: legal.address,
    email: legal.email,
    phone: legal.phone,
    whatsapp: (config.whatsappNumber || '').replace(/\D/g, ''),
  });

  return (
    <>
      <Header />
      <main className="container section legal-page">
        <header className="section-head">
          <h1 className="section-title">{t('privacy.title')}</h1>
          <p className="legal-page__date">{t('privacy.updated', { date: PRIVACY_UPDATED[lang] })}</p>
        </header>
        {!STORE_CONFIG.privacyPolicyReviewed && (
          <p className="legal-page__draft" role="note"><Info size={16} aria-hidden="true" /> {t('privacy.draft')}</p>
        )}
        {sections.map((section) => (
          <section key={section.title} className="legal-page__section">
            <h2>{section.title}</h2>
            {section.list && <ul>{section.list.map((item) => <li key={item}>{item}</li>)}</ul>}
            {(section.paragraphs || []).map((p) => <p key={p}><WithLinks text={p} /></p>)}
            {section.consentButton && trackingAvailable && (
              <button type="button" className="btn btn--soft" onClick={openConsentSettings}>{t('privacy.manageConsent')}</button>
            )}
          </section>
        ))}
      </main>
      <SiteFooter />
    </>
  );
}
