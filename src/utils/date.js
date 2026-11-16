import { currentLang } from '../i18n/I18nContext.jsx';

/** « 16 novembre 2026 » / « 16 نونبر 2026 » (chiffres latins, comme au Maroc). */
export function formatDate(iso, lang = currentLang()) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return new Intl.DateTimeFormat(lang === 'ar' ? 'ar-MA-u-nu-latn' : 'fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }).format(d);
}
