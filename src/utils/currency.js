import { STORE_CONFIG } from '../config/store.js';
import { currentLang } from '../i18n/I18nContext.jsx';

const formatter = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2, minimumFractionDigits: 0 });

/** 1290 → "1 290 DH" (arabe : "1 290 درهم", chiffres latins comme au Maroc). */
export const formatPrice = (amount) => `${formatter.format(amount)} ${currentLang() === 'ar' ? 'درهم' : STORE_CONFIG.currencyLabel}`;
