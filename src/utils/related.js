import { productStatus } from './variants.js';

/**
 * Produits à proposer en bas d'une fiche (« Vous aimerez aussi ») : uniquement des produits du catalogue
 * publié, commandables maintenant, jamais le produit consulté. D'abord ceux qui partagent le plus de
 * catégories avec lui, puis les autres, dans l'ordre du catalogue. `max` produits au plus.
 */
export function relatedProducts(products, current, max = 8) {
  const mine = new Set(current?.categories || []);
  return products
    .map((p, index) => ({ p, index, shared: p.categories.filter((c) => mine.has(c)).length }))
    .filter(({ p }) => p.id !== current?.id && productStatus(p) === 'available')
    .sort((a, b) => b.shared - a.shared || a.index - b.index)
    .slice(0, max)
    .map(({ p }) => p);
}
