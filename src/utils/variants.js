/**
 * Variantes, disponibilité et prix — logique d'AFFICHAGE commune (fiche, cartes, panier, commande).
 * Le serveur reste l'autorité : il revérifie le stock et recalcule les prix à la commande.
 *
 * Mode démo : les produits n'ont pas de variantes → tout se comporte comme avant
 * (disponible, prix du produit, pas de prix barré).
 */

export const STATUS_LABELS = {
  out_of_stock: 'Épuisé',
  unavailable: 'Indisponible',
};

const variantsOf = (product) => product?.variants || [];

export function defaultVariant(product) {
  const list = variantsOf(product);
  return list.find((v) => v.isDefault) || list[0] || null;
}

/** Variante d'une ligne de panier ; `undefined` si l'identifiant n'existe plus. */
export function findVariant(product, variantId) {
  if (variantId == null) return defaultVariant(product);
  return variantsOf(product).find((v) => v.id === variantId);
}

/** Le client doit-il choisir (au moins une option et plusieurs variantes) ? */
export const hasChoice = (product) => (product?.options?.length || 0) > 0 && variantsOf(product).length > 1;

/** Variante qui correspond exactement à une sélection { Option: valeur } (ou null). */
export function matchVariant(product, selection) {
  return variantsOf(product).find((v) => (product.options || []).every((o) => v.options?.[o.name] === selection[o.name])) || null;
}

/** 'available' | 'out_of_stock' | 'unavailable' — un stock non renseigné n'est JAMAIS disponible. */
export function variantStatus(product, variant) {
  if (!variant) return product?.inStock === false ? 'unavailable' : 'available';
  if (variant.availability) return variant.availability;
  return variant.available === false ? 'unavailable' : 'available';
}

/** État d'un produit sur une carte : disponible si au moins une variante l'est. */
export function productStatus(product) {
  const list = variantsOf(product);
  if (!list.length) return variantStatus(product, null);
  const states = list.map((v) => variantStatus(product, v));
  if (states.includes('available')) return 'available';
  return states.includes('out_of_stock') ? 'out_of_stock' : 'unavailable';
}

export const unitPrice = (product, variant) => (variant ? variant.price : product.price);

/** Prix barré seulement s'il est réellement supérieur au prix de vente (jamais de fausse promotion). */
export function compareAtPrice(product, variant) {
  const compare = variant ? variant.compareAtPrice : product.compareAtPrice;
  const price = unitPrice(product, variant);
  return typeof compare === 'number' && compare > price ? compare : null;
}

/** Libellé de la variante pour le panier et la commande (« 100 ml / Clair ») ; vide sans choix. */
export const variantLabel = (product, variant) => (variant && hasChoice(product) ? variant.title : '');

/** Clé unique d'une ligne de panier : même produit + même variante = même ligne. */
export const lineKey = ({ id, variantId }) => (variantId == null ? id : `${id}::${variantId}`);
