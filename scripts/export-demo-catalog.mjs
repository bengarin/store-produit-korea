/**
 * Exporte le catalogue de démonstration (src/data/local/) et la configuration boutique
 * (src/config/store.js) en JSON pour l'import dans MySQL :
 *   python manage.py import_demo_catalog   et   python manage.py import_store_config
 *
 * Les fichiers du front sont lus par Vite lui-même : aucune donnée recopiée à la main.
 * Usage : node scripts/export-demo-catalog.mjs
 */
import { writeFileSync } from 'node:fs';
import { createServer } from 'vite';

const OUT = 'backend/apps/catalog/fixtures/demo_catalog.json';
const OUT_CONFIG = 'backend/apps/store_settings/fixtures/demo_store_config.json';
const server = await createServer({ server: { middlewareMode: true }, appType: 'custom', logLevel: 'error' });

try {
  const { LOCAL_CATALOG } = await server.ssrLoadModule('/src/services/productService.js');
  const { LOCAL_CATEGORIES } = await server.ssrLoadModule('/src/data/local/categories.js');

  // En SSR, une image importée vaut son chemin dans le dépôt : "/src/assets/…".
  const file = (src) => (src ? src.replace(/^\//, '') : null);
  const image = (img) => ({ file: file(img.src), file640: file(img.src640), alt: img.alt, kind: img.kind || 'other', fit: img.fit });

  const products = LOCAL_CATALOG.map((p, position) => {
    const galleryIndex = p.hoverImage ? p.galleryImages.findIndex((g) => g.src === p.hoverImage.src) : -1;
    const sceneInGallery = p.galleryImages.some((g) => g.src === p.sceneImage.src);
    return {
      slug: p.id,
      position,
      brand: p.brand,
      name: p.name,
      displayName: p.displayName,
      cardLine: p.cardLine,
      price: p.price,
      categories: p.categories,
      summary: p.summary,
      highlights: p.highlights,
      ingredients: p.ingredients,
      usage: p.usage,
      benefits: p.benefits,
      skinTypes: p.skinTypes,
      gallery: p.galleryImages.map(image),
      scene: sceneInGallery ? null : image(p.sceneImage),
      hover: galleryIndex >= 0 ? { galleryIndex, position: p.hoverImage.position || '' } : null,
    };
  });

  const categories = LOCAL_CATEGORIES.map((c, position) => ({ slug: c.id, name: c.label, position }));
  writeFileSync(OUT, `${JSON.stringify({ source: 'src/data/local', categories, products }, null, 2)}\n`);
  console.log(`${products.length} produits, ${categories.length} catégories → ${OUT}`);

  const { STORE_CONFIG } = await server.ssrLoadModule('/src/config/store.js');
  const { MAX_QTY } = await server.ssrLoadModule('/src/services/cartService.js');
  const config = {
    source: 'src/config/store.js',
    brandName: STORE_CONFIG.brandName,
    whatsappNumber: STORE_CONFIG.whatsappNumber,
    deliveryFee: STORE_CONFIG.deliveryFee,
    freeDeliveryThreshold: STORE_CONFIG.freeDeliveryThreshold,
    cities: STORE_CONFIG.cities,
    promoCodes: STORE_CONFIG.promoCodes,
    maxQtyPerLine: MAX_QTY,
  };
  writeFileSync(OUT_CONFIG, `${JSON.stringify(config, null, 2)}\n`);
  console.log(`${config.cities.length} villes, ${Object.keys(config.promoCodes).length} code(s) promo → ${OUT_CONFIG}`);
} finally {
  await server.close();
}
