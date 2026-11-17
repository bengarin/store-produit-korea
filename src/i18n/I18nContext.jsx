import { createContext, Fragment, useCallback, useContext, useLayoutEffect, useMemo, useState } from 'react';
import { MESSAGES } from './messages.js';
import { translateContent } from './content.js';
import { storeLang, urlFor, urlLang } from './langUrl.js';

/**
 * Langue de la boutique publique : français (défaut) ou arabe (RTL).
 * - donnée par l'ADRESSE : /… en français, /ar/… en arabe (pages indexables séparément, voir langUrl.js) ;
 * - choix mémorisé dans le navigateur (localStorage) pour les visites suivantes ;
 * - <html lang/dir> mis à jour ; remis en français/LTR en quittant la boutique (administration) ;
 * - `t(clé, paramètres)` : textes de l'interface ; `tc(texte)` : textes de contenu (thème, catégories…)
 *   traduits seulement s'ils correspondent exactement à un texte d'origine connu (sinon affichés tels quels).
 */
export const LANGS = { fr: { dir: 'ltr', label: 'Français' }, ar: { dir: 'rtl', label: 'العربية' } };
// Police arabe (les polices latines de la marque n'ont pas de glyphes arabes). Chargée seulement en arabe.
const ARABIC_FONTS = 'https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@500;600;700&family=Noto+Sans+Arabic:wght@400;500;600;700&display=swap';

let current = 'fr';
/** Langue active (pour les fonctions hors composants : prix, lien WhatsApp…). */
export const currentLang = () => current;

export function translate(lang, key, params = {}) {
  const entry = MESSAGES[lang]?.[key] ?? MESSAGES.fr[key];
  if (entry === undefined) {
    if (import.meta.env.DEV) console.warn(`Texte manquant : ${key}`);
    return key;
  }
  return typeof entry === 'function' ? entry(params) : entry;
}

const I18nContext = createContext({
  lang: 'fr', dir: 'ltr', setLang: () => {}, t: (k, p) => translate('fr', k, p), tx: (k) => k, tc: (s) => s, autoDir: undefined,
});

/**
 * `lang` / `onLangChange` : réservés à l'aperçu de l'administration (langue imposée, sans changer d'adresse).
 * La boutique ne les passe jamais : la langue y vient de l'adresse.
 */
export function I18nProvider({ children, lang: forcedLang, onLangChange }) {
  const [urlLanguage] = useState(() => urlLang());
  const lang = forcedLang === 'ar' || forcedLang === 'fr' ? forcedLang : urlLanguage;
  current = lang; // lu par formatPrice pendant ce rendu

  useLayoutEffect(() => {
    const root = document.documentElement;
    root.lang = lang;
    if (lang === 'ar') root.dir = 'rtl';
    else root.removeAttribute('dir');
    let link = null;
    if (lang === 'ar' && !document.querySelector('link[data-arabic-font]')) {
      link = Object.assign(document.createElement('link'), { rel: 'stylesheet', href: ARABIC_FONTS });
      link.dataset.arabicFont = '1';
      document.head.appendChild(link);
    }
    return () => link?.remove();
  }, [lang]);

  // En quittant la boutique (ex. vers l'administration) : retour au français, de gauche à droite.
  useLayoutEffect(() => () => {
    document.documentElement.lang = 'fr';
    document.documentElement.removeAttribute('dir');
    document.querySelector('link[data-arabic-font]')?.remove();
    current = 'fr';
  }, []);

  // Changer de langue = aller à la même page dans l'autre langue (adresse /ar/… ou sans préfixe).
  const setLang = useCallback((next) => {
    const value = next === 'ar' ? 'ar' : 'fr';
    if (onLangChange) {
      onLangChange(value); // aperçu : ni mémorisation ni changement d'adresse
      return;
    }
    storeLang(value);
    if (value !== urlLang()) window.location.assign(urlFor(value));
  }, [onLangChange]);

  const value = useMemo(() => {
    const t = (key, params) => translate(lang, key, params);
    /**
     * Texte avec éléments React : « Code {code} appliqué » + { code: <strong/> } → ['Code ', <strong/>, ' appliqué'].
     */
    const tx = (key, nodes = {}) => {
      const text = translate(lang, key, nodes);
      return text.split(/(\{\w+\})/).filter((part) => part !== '').map((part, i) => {
        const name = /^\{(\w+)\}$/.exec(part)?.[1];
        return <Fragment key={i}>{name && name in nodes ? nodes[name] : part}</Fragment>;
      });
    };
    return {
      lang,
      dir: LANGS[lang].dir,
      setLang,
      t,
      tx,
      tc: (text) => (lang === 'fr' ? text : translateContent(lang, text)),
      // Contenu saisi par l'équipe (souvent en français) dans une page arabe : sens détecté par paragraphe.
      autoDir: lang === 'fr' ? undefined : 'auto',
    };
  }, [lang, setLang]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export const useI18n = () => useContext(I18nContext);
