/**
 * Recherche produits côté navigateur (le catalogue public est déjà chargé en entier).
 * - Insensible aux majuscules et aux accents (« creme » trouve « Crème »).
 * - Arabe : voyelles courtes ignorées, alif / ya / ta marbuta unifiés.
 * - Cherche en français ET en arabe, quelle que soit la langue affichée.
 * - Tous les mots doivent être trouvés ; le nom et la marque comptent plus que la description.
 */

const AR_DIACRITICS = /[ً-ٰٟـ]/g; // tashkil + tatweel

export function normalize(text) {
  return String(text ?? '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '') // accents latins
    .replace(AR_DIACRITICS, '')
    .replace(/[إأآا]/g, 'ا')
    .replace(/ى/g, 'ي')
    .replace(/ة/g, 'ه')
    .replace(/<[^>]*>/g, ' ') // descriptions HTML
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim();
}

/** Mots de la recherche ; pluriel français simple retiré (« crèmes » → « creme »). */
export function terms(query) {
  return normalize(query)
    .split(' ')
    .filter(Boolean)
    .map((w) => (w.length > 3 && /[a-z][sx]$/.test(w) ? w.slice(0, -1) : w));
}

const flat = (v) => (Array.isArray(v) ? v.map((x) => (typeof x === 'object' ? x?.label : x)).join(' ') : v || '');

/** Textes indexés d'un produit (non traduit + traductions), en 3 niveaux d'importance. */
export function indexProduct(raw, categoryLabels = []) {
  const langs = [raw, ...Object.values(raw.translations || {})];
  const pick = (keys) => normalize(langs.flatMap((src) => keys.map((k) => flat(src?.[k]))).join(' '));
  return {
    title: pick(['displayName', 'brand', 'name']),
    tags: `${pick(['cardLine', 'skinTypes', 'highlights'])} ${normalize(categoryLabels.join(' '))}`,
    body: pick(['summary', 'ingredients', 'benefits', 'usage', 'descriptionHtml']),
  };
}

/** Score d'un index pour des mots donnés : 0 = au moins un mot introuvable. */
export function score(index, words) {
  let total = 0;
  for (const w of words) {
    const s = index.title.includes(w) ? 3 : index.tags.includes(w) ? 2 : index.body.includes(w) ? 1 : 0;
    if (!s) return 0;
    total += s;
  }
  return total;
}

/**
 * Produits correspondant à la recherche, les plus pertinents d'abord (ordre du catalogue à égalité).
 * `entries` : [{ product, index }] ; recherche vide → tous les produits, dans l'ordre.
 */
export function searchEntries(entries, query) {
  const words = terms(query);
  if (!words.length) return entries.map((e) => e.product);
  return entries
    .map((e, i) => ({ p: e.product, s: score(e.index, words), i }))
    .filter((r) => r.s > 0)
    .sort((a, b) => b.s - a.s || a.i - b.i)
    .map((r) => r.p);
}
