/**
 * Filtres de la page produits, lus et écrits dans l'adresse (partageable, conservés au retour arrière) :
 *   ?categorie=hydratation&prix_min=100&prix_max=250&filtres=mes-solutions:hydratation,type-de-peau:seche&tri=prix-asc
 * Règle : dans un même groupe, une valeur OU une autre ; entre groupes, ET.
 */

export const SORTS = ['recommandes', 'prix-asc', 'prix-desc', 'nouveautes'];
const FILTER_KEYS = ['categorie', 'prix_min', 'prix_max', 'filtres'];

export function readFilters(params) {
  const options = {};
  (params.get('filtres') || '').split(',').filter(Boolean).forEach((pair) => {
    const [group, option] = pair.split(':');
    if (group && option) (options[group] ||= []).push(option);
  });
  const min = params.get('prix_min');
  const max = params.get('prix_max');
  let price = null;
  if (min !== null || max !== null) {
    const lo = min === null || min === '' ? 0 : Number(min);
    const hi = max === null || max === '' ? Infinity : Number(max);
    if (!Number.isNaN(lo) && !Number.isNaN(hi) && lo >= 0 && lo <= hi) price = { min: lo, max: hi };
  }
  const sort = SORTS.includes(params.get('tri')) ? params.get('tri') : 'recommandes';
  return { category: params.get('categorie') || 'all', price, options, sort };
}

/** Écrit les filtres dans l'adresse en gardant les autres paramètres (recherche, favoris, ingrédient…). */
export function writeFilters(params, { category, price, options, sort }) {
  const next = new URLSearchParams(params);
  FILTER_KEYS.forEach((k) => next.delete(k));
  if (category && category !== 'all') next.set('categorie', category);
  if (price) {
    next.set('prix_min', String(price.min));
    if (Number.isFinite(price.max)) next.set('prix_max', String(price.max));
  }
  const pairs = Object.entries(options || {}).flatMap(([g, list]) => list.map((o) => `${g}:${o}`));
  if (pairs.length) next.set('filtres', pairs.join(','));
  if (sort && sort !== 'recommandes') next.set('tri', sort);
  else next.delete('tri');
  return next;
}

export const activeCount = ({ category, price, options }) =>
  (category !== 'all' ? 1 : 0) + (price ? 1 : 0) + Object.values(options).reduce((n, l) => n + l.length, 0);

/** Le produit passe-t-il les filtres ? `skip` = groupe ignoré (pour compter les produits d'une valeur). */
export function matches(product, state, { inCategory, skip = null } = {}) {
  if (skip !== 'category' && state.category !== 'all' && !inCategory(product, state.category)) return false;
  if (skip !== 'price' && state.price && !(product.price >= state.price.min && product.price <= state.price.max)) return false;
  for (const [group, list] of Object.entries(state.options)) {
    if (group === skip || !list.length) continue;
    if (!list.some((o) => product.filters.includes(`${group}:${o}`))) return false;
  }
  return true;
}

export function sortProducts(list, sort) {
  if (sort === 'recommandes') return list;
  const out = [...list];
  if (sort === 'prix-asc') out.sort((a, b) => a.price - b.price);
  else if (sort === 'prix-desc') out.sort((a, b) => b.price - a.price);
  else if (sort === 'nouveautes') out.sort((a, b) => (b.publishedAt || '').localeCompare(a.publishedAt || ''));
  return out;
}

/** Nombre de produits par valeur (en tenant compte des AUTRES filtres) : « Hydratation (4) ». */
export function optionCounts(products, state, groups, ctx) {
  const counts = {};
  groups.forEach((g) => {
    const base = products.filter((p) => matches(p, state, { ...ctx, skip: g.id }));
    g.options.forEach((o) => {
      counts[`${g.id}:${o.id}`] = base.filter((p) => p.filters.includes(`${g.id}:${o.id}`)).length;
    });
  });
  return counts;
}
