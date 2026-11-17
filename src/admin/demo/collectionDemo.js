/**
 * Données FICTIVES pour l'aperçu d'une collection dans l'administration (« TEST — données fictives »).
 * - Jamais envoyées au serveur, jamais enregistrées : elles n'existent que dans cette page d'aperçu.
 * - Aucun lien avec les vrais produits : identifiants « test-… », marque « TEST ».
 * - Aucun pays de fabrication renseigné (pas de champ `origin`) : aucune origine n'est affirmée.
 * Format identique à l'API publique, pour passer par la même normalisation que la boutique.
 */

const PALETTES = [
  ['#e9dccb', '#c9b08f'],
  ['#dfe7dc', '#9fb79a'],
  ['#f1dcd6', '#d39c8e'],
  ['#e2e0ec', '#a7a1c4'],
  ['#efe6cf', '#cfb56f'],
  ['#d9e6e6', '#8fb3b3'],
];

/** Image fictive (SVG en ligne) : dégradé + « TEST — image fictive ». Aucune photo réelle. */
function demoImage(n) {
  const [a, b] = PALETTES[(n - 1) % PALETTES.length];
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="900" height="900" viewBox="0 0 900 900">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient></defs>
<rect width="900" height="900" fill="url(#g)"/>
<rect x="330" y="250" width="240" height="380" rx="36" fill="#fffaf2" opacity=".85"/>
<rect x="380" y="200" width="140" height="70" rx="14" fill="#fffaf2" opacity=".7"/>
<text x="450" y="455" font-family="Arial, sans-serif" font-size="58" font-weight="700" fill="#7a2e20" text-anchor="middle">TEST</text>
<text x="450" y="760" font-family="Arial, sans-serif" font-size="34" fill="#3b3a36" text-anchor="middle">Image fictive · ${n}</text>
</svg>`;
  return { src: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`, alt: `TEST — image fictive ${n}`, kind: 'product', fit: 'cover' };
}

export const DEMO_CATEGORY = 'test-exemple';
export const DEMO_FILTER_GROUP = 'test-besoin';

const ITEMS = [
  { n: 1, fr: 'Crème hydratante', ar: 'كريم مرطب', price: 189, filter: 'hydratation' },
  { n: 2, fr: 'Sérum éclat', ar: 'سيروم الإشراقة', price: 249, compareAt: 299, filter: 'eclat' },
  { n: 3, fr: 'Masque en tissu', ar: 'قناع قماشي', price: 39, filter: 'hydratation' },
  { n: 4, fr: 'Lotion tonique', ar: 'لوشن منعش', price: 159, filter: 'eclat' },
  { n: 5, fr: 'Contour des yeux', ar: 'كريم محيط العين', price: 219, filter: 'hydratation', soldOut: true },
  { n: 6, fr: 'Huile démaquillante', ar: 'زيت مزيل للمكياج', price: 139, filter: 'eclat' },
];

/** Produits fictifs rattachés à la collection prévisualisée (et à elle seule). */
export function demoProducts(collectionSlug) {
  return ITEMS.map((it) => {
    const id = `test-${it.n}`;
    const image = demoImage(it.n);
    return {
      id,
      slug: id,
      brand: 'TEST',
      name: `Produit fictif ${it.n}`,
      displayName: `TEST · ${it.fr} (exemple ${it.n})`,
      cardLine: 'Texte de démonstration — produit fictif, non vendu.',
      price: it.price,
      compareAtPrice: it.compareAt ?? null,
      categories: [DEMO_CATEGORY],
      filters: [`${DEMO_FILTER_GROUP}:${it.filter}`],
      collections: [collectionSlug],
      // Pas de champ `origin` : le pays de fabrication n'est PAS renseigné (volontaire).
      publishedAt: new Date(Date.UTC(2026, 0, it.n)).toISOString(),
      inStock: !it.soldOut,
      images: [image],
      options: [],
      variants: [{
        id: `${id}-v`, title: 'Default', sku: `TEST-${it.n}`, price: it.price, compareAtPrice: it.compareAt ?? null,
        available: !it.soldOut, availability: it.soldOut ? 'out_of_stock' : 'available', isDefault: true, options: {}, image: null,
      }],
      translations: {
        ar: {
          displayName: `اختبار · ${it.ar} (مثال ${it.n})`,
          cardLine: 'نص تجريبي — منتج وهمي غير معروض للبيع.',
        },
      },
    };
  });
}

export const DEMO_CATEGORIES = [
  { id: DEMO_CATEGORY, label: 'TEST — exemple', translations: { ar: { label: 'اختبار — مثال' } } },
];

export const DEMO_FILTERS = [
  {
    id: DEMO_FILTER_GROUP,
    label: 'Besoin (exemple)',
    translations: { ar: { label: 'الحاجة (مثال)' } },
    options: [
      { id: 'hydratation', label: 'Hydratation (exemple)', translations: { ar: { label: 'ترطيب (مثال)' } } },
      { id: 'eclat', label: 'Éclat (exemple)', translations: { ar: { label: 'إشراقة (مثال)' } } },
    ],
  },
];

/**
 * Collection au format public, à partir des textes RÉELS saisis dans Admin → Collections (lecture seule).
 * Sans image choisie : la 1re image fictive (comme la boutique prend la photo du 1er produit).
 */
export function demoCollection(c, products) {
  const image = c.image ? { src: c.image.src, alt: c.imageAlt || c.image.alt || '', fit: 'cover' } : products[0].images[0];
  const ar = Object.fromEntries(Object.entries({ label: c.nameAr, description: c.descriptionAr }).filter(([, v]) => v));
  return {
    id: c.slug,
    label: c.name,
    description: c.description,
    image,
    productCount: products.length,
    ...(Object.keys(ar).length ? { translations: { ar } } : {}),
  };
}
