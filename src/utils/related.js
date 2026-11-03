import { productStatus } from './variants.js';

export const RELATED_MIN = 4;
export const RELATED_MAX = 8;

/**
 * Produits à proposer en bas d'une fiche (« Vous aimerez aussi »), tous issus du catalogue publié :
 * 1. jamais le produit consulté (comparaison par identifiant), jamais deux fois le même produit ;
 * 2. d'abord les produits commandables maintenant, ceux qui partagent le plus de catégories en premier ;
 * 3. s'il y en a moins de `min`, la liste est complétée par d'autres produits publiés (même ordre de priorité) :
 *    leur carte affiche alors « Indisponible » ou « Épuisé » et le bouton panier est désactivé, comme au catalogue.
 * `max` produits au plus.
 */
export function relatedProducts(products, current, { min = RELATED_MIN, max = RELATED_MAX } = {}) {
  const currentId = current?.id;
  const mine = new Set(current?.categories || []);
  const seen = new Set([currentId]);
  const ranked = [];
  products.forEach((p, index) => {
    if (!p?.id || seen.has(p.id)) return;
    seen.add(p.id);
    ranked.push({ p, index, available: productStatus(p) === 'available', shared: (p.categories || []).filter((c) => mine.has(c)).length });
  });
  ranked.sort((a, b) => b.shared - a.shared || a.index - b.index);
  const available = ranked.filter((r) => r.available);
  const others = ranked.filter((r) => !r.available);
  const list = available.length >= min ? available : [...available, ...others.slice(0, min - available.length)];
  return list.slice(0, max).map(({ p }) => p);
}
