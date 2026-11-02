/**
 * Consentement aux cookies publicitaires (pixel Meta).
 * - Aucun script Meta n'est chargé et aucune donnée n'est envoyée tant que le visiteur n'a pas accepté.
 * - Le choix (accepté / refusé) est mémorisé dans le navigateur ; il peut être changé à tout moment
 *   (lien « Cookies » du pied de page).
 */
import { DATA_SOURCE } from '../config/env.js';

const STORAGE_KEY = 'mpc.consent.ads';

/** Identifiant public du pixel (pas un secret). `VITE_META_PIXEL_ID=off` désactive le pixel. */
const rawPixelId = (import.meta.env.VITE_META_PIXEL_ID ?? '1665012938525216').trim();
export const META_PIXEL_ID = /^\d{10,20}$/.test(rawPixelId) ? rawPixelId : '';

const inPreview = typeof window !== 'undefined'
  && (new URLSearchParams(window.location.search).has('apercu-theme') || window.parent !== window);

/**
 * Le suivi n'existe que sur la vraie boutique : mode API (vraies commandes, vrais produits), pixel configuré,
 * hors aperçu de l'éditeur de thème. Le mode démo (commandes simulées) n'envoie jamais rien.
 */
export const trackingAvailable = DATA_SOURCE === 'api' && Boolean(META_PIXEL_ID) && !inPreview;

let listeners = [];

/** 'granted' | 'denied' | null (pas encore choisi). */
export function getConsent() {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value === 'granted' || value === 'denied' ? value : null;
  } catch {
    return null;
  }
}

export function setConsent(value) {
  try {
    window.localStorage.setItem(STORAGE_KEY, value);
  } catch {
    /* stockage bloqué : le choix vaut pour cette page */
  }
  listeners.forEach((fn) => fn({ consent: value, open: false }));
}

/** Rouvre le bandeau pour changer d'avis. */
export function openConsentSettings() {
  listeners.forEach((fn) => fn({ consent: getConsent(), open: true }));
}

export function onConsentChange(fn) {
  listeners.push(fn);
  return () => { listeners = listeners.filter((l) => l !== fn); };
}
