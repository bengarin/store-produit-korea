/**
 * Vérifie que l'API publique du backend renvoie EXACTEMENT les données du catalogue local du front
 * (après passage dans normalizeProduct, comme le fait l'application). Les chemins d'images sont
 * comparés par nom de fichier (seul l'hébergement de l'image change).
 *
 * Usage : backend lancé (python manage.py runserver) et catalogue importé, puis
 *   node scripts/check-api-contract.mjs [http://127.0.0.1:8000/api/v1/store]
 */
import { createServer } from 'vite';
const BASE = process.argv[2] || 'http://127.0.0.1:8000/api/v1/store';
const server = await createServer({ server: { middlewareMode: true }, appType: 'custom', logLevel: 'error' });
const { LOCAL_CATALOG, normalizeProduct } = await server.ssrLoadModule('/src/services/productService.js');
const { LOCAL_CATEGORIES } = await server.ssrLoadModule('/src/data/local/categories.js');
await server.close();
const api = (await (await fetch(`${BASE}/products`)).json()).items.map((p) => normalizeProduct(p, p));
const cats = (await (await fetch(`${BASE}/categories`)).json()).items;
// Comparaison indépendante de l'ordre des clés d'un objet.
const canon = (v) => (Array.isArray(v) ? v.map(canon) : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, canon(v[k])])) : v);
const norm = (v) => canon( JSON.parse(JSON.stringify(v, (k, x) => (typeof x === 'string' && /\.(webp|png)$/.test(x) ? x.split('/').pop() : x))));
// Données de vente propres au backend (le mode démo n'a ni variantes ni stock) : non comparées.
const API_ONLY = new Set(['variants', 'inStock']);
let diffs = 0;
if (JSON.stringify(cats) !== JSON.stringify(LOCAL_CATEGORIES)) { diffs++; console.log('CATEGORIES', cats, LOCAL_CATEGORIES); }
if (api.length !== LOCAL_CATALOG.length) { diffs++; console.log('COUNT', api.length); }
LOCAL_CATALOG.forEach((local, i) => {
  const remote = norm(api[i]); const l = norm(local);
  for (const key of Object.keys(l).filter((k) => !API_ONLY.has(k))) {
    if (JSON.stringify(l[key]) !== JSON.stringify(remote[key])) { diffs++; console.log(local.id, key, '\n local:', JSON.stringify(l[key]), '\n api  :', JSON.stringify(remote[key])); }
  }
});
console.log('DIFFERENCES', diffs);
process.exitCode = diffs ? 1 : 0;
