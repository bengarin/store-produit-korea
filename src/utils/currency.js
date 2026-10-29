import { STORE_CONFIG } from '../config/store.js';

const formatter = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2, minimumFractionDigits: 0 });

/** 1290 → "1 290 DH" */
export const formatPrice = (amount) => `${formatter.format(amount)} ${STORE_CONFIG.currencyLabel}`;
