import { Languages } from 'lucide-react';
import { LANGS, useI18n } from '../i18n/I18nContext.jsx';

/**
 * Choix de la langue. En-tête : un bouton qui propose l'autre langue (« العربية » / « Français »).
 * Menu mobile (`full`) : les deux langues, la langue active étant cochée.
 */
export default function LanguageSwitcher({ full = false, className = '' }) {
  const { lang, setLang, t } = useI18n();
  if (full) {
    return (
      <div className={`lang-switch lang-switch--full ${className}`} role="group" aria-label={t('lang.group')}>
        <Languages size={18} aria-hidden="true" />
        {Object.entries(LANGS).map(([code, { label }]) => (
          <button key={code} type="button" lang={code} aria-pressed={lang === code}
            className={`lang-switch__option ${lang === code ? 'is-active' : ''}`} onClick={() => setLang(code)}>
            {label}
          </button>
        ))}
      </div>
    );
  }
  const other = lang === 'ar' ? 'fr' : 'ar';
  return (
    <button type="button" className={`lang-switch ${className}`} lang={other} onClick={() => setLang(other)} aria-label={t('lang.switchTo')}>
      {LANGS[other].label}
    </button>
  );
}
