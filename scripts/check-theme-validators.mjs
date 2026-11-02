/**
 * Le validateur du navigateur (src/theme/validate.js) doit rendre le même verdict que celui du serveur
 * (backend/apps/themes/validation.py, testé par pytest) sur les cas partagés shared/theme/test-cases.json.
 * Usage : node scripts/check-theme-validators.mjs
 */
import { readFileSync } from 'node:fs';
import { createServer } from 'vite';

const server = await createServer({ server: { middlewareMode: true }, appType: 'custom', logLevel: 'error' });
const { validateTheme } = await server.ssrLoadModule('/src/theme/validate.js');
await server.close();
const base = JSON.parse(readFileSync(new URL('../shared/theme/default-theme.json', import.meta.url)));
const { cases } = JSON.parse(readFileSync(new URL('../shared/theme/test-cases.json', import.meta.url)));

// Comparaison indépendante de l'ordre des clés.
const canon = (v) => (Array.isArray(v) ? v.map(canon) : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, canon(v[k])])) : v);
let failures = 0;
for (const c of cases) {
  const theme = structuredClone(base);
  for (const op of c.ops) {
    const keys = [...op.path];
    const last = keys.pop();
    const target = keys.reduce((t, k) => t[k], theme);
    if (op.op === 'set') target[last] = structuredClone(op.value);
    else target[last].push(structuredClone(op.value));
  }
  const { ok, errors, value } = validateTheme(theme);
  const paths = errors.map((e) => e.path);
  const good = ok === c.valid && (c.valid || paths.includes(c.path));
  if (!good) failures++;
  console.log(good ? '  ✓' : '  ✗', c.name, good ? '' : JSON.stringify(errors));
  if (c.name === 'thème par défaut' && JSON.stringify(canon(value)) !== JSON.stringify(canon(base))) { failures++; console.log('  ✗ normalisation du thème par défaut'); }
}
console.log(`CAS ${cases.length} — ÉCARTS ${failures}`);
process.exitCode = failures ? 1 : 0;
