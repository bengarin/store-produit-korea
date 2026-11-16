/**
 * Langue de la boutique portée par l'ADRESSE (G1) : français aux adresses historiques (/, /produits…),
 * arabe sous /ar (/ar, /ar/produits…). Chaque langue a ses propres pages indexables (hreflang côté serveur).
 */
export const AR_PREFIX = '/ar';
export const STORAGE_KEY = 'mpc.lang';

export const isArabicPath = (pathname) => pathname === AR_PREFIX || pathname.startsWith(`${AR_PREFIX}/`);

/** Langue de l'adresse courante. */
export const urlLang = (pathname = window.location.pathname) => (isArabicPath(pathname) ? 'ar' : 'fr');

/** Base du routeur : les liens internes (« /produits ») deviennent « /ar/produits » en arabe. */
export const routerBasename = (pathname = window.location.pathname) => (isArabicPath(pathname) ? AR_PREFIX : '');

/** Même page dans l'autre langue (paramètres et ancre conservés). */
export function urlFor(lang, loc = window.location) {
  const path = isArabicPath(loc.pathname) ? loc.pathname.slice(AR_PREFIX.length) || '/' : loc.pathname;
  const target = lang === 'ar' ? (path === '/' ? AR_PREFIX : `${AR_PREFIX}${path}`) : path;
  return `${target}${loc.search}${loc.hash}`;
}

export function storedLang() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === 'ar' ? 'ar' : 'fr';
  } catch {
    return 'fr';
  }
}

export function storeLang(lang) {
  try {
    window.localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* stockage bloqué : le choix vaut pour cette visite */
  }
}
