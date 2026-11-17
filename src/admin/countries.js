/** Pays de fabrication (codes ISO) — même liste que le serveur (apps.catalog.models.ORIGIN_COUNTRIES). */
export const COUNTRIES = [
  ['KR', 'Corée du Sud'], ['CN', 'Chine'], ['JP', 'Japon'], ['TW', 'Taïwan'], ['TH', 'Thaïlande'],
  ['FR', 'France'], ['ES', 'Espagne'], ['IT', 'Italie'], ['DE', 'Allemagne'], ['GB', 'Royaume-Uni'],
  ['CH', 'Suisse'], ['US', 'États-Unis'], ['MA', 'Maroc'],
];
export const countryName = (code) => COUNTRIES.find(([c]) => c === code)?.[1] || '';

/**
 * Raisons pour lesquelles un produit ne peut pas entrer dans une collection (même règle que le serveur, qui vérifie
 * de toute façon) : pays de fabrication exigé, liste d'ingrédients exigée.
 */
export function collectionIssues(collection, { origin, ingredients }) {
  const issues = [];
  if (collection.requiredOrigin && origin !== collection.requiredOrigin) {
    issues.push(`pays de fabrication « ${countryName(collection.requiredOrigin)} » requis`);
  }
  if (collection.requireIngredients && !(ingredients || []).some((i) => String(i).trim())) {
    issues.push('liste des ingrédients à renseigner');
  }
  return issues;
}

/** Règles d'une collection, en clair. */
export function collectionRules(collection) {
  const rules = [];
  if (collection.requiredOrigin) rules.push(`Fabriqué en ${countryName(collection.requiredOrigin)} uniquement`);
  if (collection.requireIngredients) rules.push('Liste d’ingrédients obligatoire');
  return rules;
}
