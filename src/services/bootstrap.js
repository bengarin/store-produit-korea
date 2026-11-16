/**
 * Données de démarrage jointes par le serveur à la page HTML (<script id="mpc-data" type="application/json">) :
 * produits, catégories, filtres, configuration et thème publiés — les mêmes réponses que les API publiques.
 * Lues une seule fois : le premier affichage n'attend plus le réseau. Absentes (serveur de développement Vite,
 * erreur de lecture) : `null`, et l'application appelle les API comme avant.
 */
let cache;

export function bootstrapData() {
  if (cache !== undefined) return cache;
  cache = null;
  try {
    const el = typeof document !== 'undefined' ? document.getElementById('mpc-data') : null;
    if (el) cache = JSON.parse(el.textContent);
  } catch {
    cache = null;
  }
  return cache;
}
