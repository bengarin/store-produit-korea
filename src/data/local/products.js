/**
 * 🧴 CATALOGUE PRODUITS (données locales de démonstration)
 *
 * - Prix : valeurs PROVISOIRES [DÉMO] → modifiez `price` (en DH).
 * - Photos : voir src/data/local/productImages.js (un dossier par produit dans
 *   src/assets/products/<id>/).
 * - Ce fichier est la SOURCE LOCALE : il sera remplacé par l'API (GET /products).
 * - Textes : contenu INDICATIF basé sur le nom du produit. À valider avec
 *   l'emballage / la fiche officielle de la marque avant la mise en ligne.
 *   Aucune allégation médicale ou dermatologique n'est faite ici.
 */
/**
 * Forme « brute » d'un produit, identique à ce que renverra GET /products (voir docs/BACKEND.md).
 * Les images sont rattachées par productService (src/data/local/productImages.js).
 * `highlights[].icon` = nom d'icône (voir src/utils/icons.js), pas un composant.
 */
export const LOCAL_PRODUCTS = [
  {
    id: 'baroness-aloe-vera-gel',
    cardLine: "Gel à l'aloe vera, frais et léger.",
    brand: 'Baroness',
    name: 'Aloe Vera Soothing Gel',
    displayName: 'Baroness Aloe Vera Soothing Gel',
    price: 129, // [DÉMO]
    categories: ['hydratation'],
    summary:
      "Gel à l'aloe vera à la texture fraîche et légère, pensé pour le visage et le corps.",
    highlights: [
      { icon: 'leaf', label: "À l'aloe vera" },
      { icon: 'droplets', label: 'Texture gel' },
      { icon: 'hand', label: 'Visage & corps' },
      { icon: 'sun', label: 'Usage quotidien' },
    ],
    ingredients: [
      'Aloe vera (ingrédient principal indiqué dans le nom du produit)',
      "Liste INCI complète : à reprendre de l'emballage officiel",
    ],
    usage: [
      'Appliquer une petite quantité sur une peau propre.',
      "Masser légèrement jusqu'à absorption.",
      "Suivre les indications de l'emballage.",
    ],
    benefits: [
      'Sensation de fraîcheur à l’application',
      'Texture légère, non grasse au toucher',
      'Format polyvalent visage et corps',
    ],
    skinTypes: "À confirmer selon la fiche officielle du produit.",
  },
  {
    id: 'some-by-mi-yuja-niacin-cream',
    cardLine: 'Crème au Yuja et à la niacinamide.',
    brand: 'SOME BY MI',
    name: 'Yuja Niacin Anti Blemish Cream',
    displayName: 'SOME BY MI Yuja Niacin Cream',
    price: 199, // [DÉMO]
    categories: ['eclat'],
    summary:
      'Une crème formulée avec du Yuja (agrume coréen) et de la niacinamide, pour une routine axée sur l’éclat du teint.',
    highlights: [
      { icon: 'citrus', label: 'Extrait de Yuja' },
      { icon: 'flask', label: 'Niacinamide' },
      { icon: 'sparkles', label: 'Routine éclat' },
      { icon: 'sun', label: 'Usage quotidien' },
    ],
    ingredients: [
      'Extrait de Yuja (citron coréen)',
      'Niacinamide',
      "Liste INCI complète : à reprendre de l'emballage officiel",
    ],
    usage: [
      'Après le nettoyage et le tonique, prélever une petite quantité.',
      'Appliquer sur le visage en évitant le contour des yeux.',
      'Faire pénétrer par légers tapotements.',
    ],
    benefits: [
      'S’intègre dans une routine orientée éclat',
      'Texture crème confortable',
      'Associe Yuja et niacinamide',
    ],
    skinTypes: "À confirmer selon la fiche officielle du produit.",
  },
  {
    id: 'biovene-eye-patches',
    cardLine: 'Patchs contour des yeux, tripeptide et concombre.',
    brand: 'BIOVÈNE',
    name: 'Tripeptide Cucumber Age-Defy Under Eye Patches',
    displayName: 'Biovène Eye Patches',
    price: 149, // [DÉMO]
    categories: ['anti-age'],
    summary:
      'Patchs pour le contour des yeux associant tripeptide et concombre, pour un moment de soin rapide.',
    highlights: [
      { icon: 'eye', label: 'Contour des yeux' },
      { icon: 'flask', label: 'Tripeptide' },
      { icon: 'leaf', label: 'Concombre' },
      { icon: 'clock', label: 'Pose rapide' },
    ],
    ingredients: [
      'Tripeptide',
      'Extrait de concombre',
      "Liste INCI complète : à reprendre de l'emballage officiel",
    ],
    usage: [
      'Sur une peau propre et sèche, placer un patch sous chaque œil.',
      "Laisser poser le temps indiqué sur l'emballage.",
      'Retirer et faire pénétrer le reste de produit du bout des doigts.',
    ],
    benefits: [
      'Geste simple pour le contour des yeux',
      'Sensation de fraîcheur',
      'Format pratique à garder dans sa routine',
    ],
    skinTypes: "À confirmer selon la fiche officielle du produit.",
  },
  {
    id: 'vitamin-collagen-vital-cream',
    cardLine: 'Crème riche aux vitamines et au collagène.',
    brand: 'Quret', // marque lisible sur l'emballage
    name: 'Vitamin Collagen Vital Cream',
    displayName: 'Quret Vitamin Collagen Vital Cream',
    price: 229, // [DÉMO]
    categories: ['anti-age', 'eclat'],
    summary:
      'Crème associant vitamines et collagène, pour une routine de soin riche et confortable.',
    highlights: [
      { icon: 'sparkles', label: 'Vitamines' },
      { icon: 'layers', label: 'Collagène' },
      { icon: 'droplets', label: 'Texture crème' },
      { icon: 'sun', label: 'Matin & soir' },
    ],
    ingredients: [
      'Vitamines (selon le nom du produit)',
      'Collagène',
      "Liste INCI complète : à reprendre de l'emballage officiel",
    ],
    usage: [
      'Appliquer en dernière étape de la routine, matin et/ou soir.',
      'Masser du centre du visage vers l’extérieur.',
      "Suivre les indications de l'emballage.",
    ],
    benefits: [
      'Texture riche et confortable',
      'Associe vitamines et collagène',
      'Convient comme crème de fin de routine',
    ],
    skinTypes: "À confirmer selon la fiche officielle du produit.",
  },
  {
    id: 'orjena-power-collagen-emulsion',
    cardLine: 'Émulsion fluide au collagène.',
    brand: 'ORJENA',
    name: 'Power Collagen Emulsion',
    displayName: 'ORJENA Power Collagen Emulsion',
    price: 179, // [DÉMO]
    categories: ['hydratation', 'anti-age'],
    summary:
      'Émulsion fluide au collagène, à utiliser comme étape légère de la routine coréenne.',
    highlights: [
      { icon: 'layers', label: 'Collagène' },
      { icon: 'droplets', label: 'Texture fluide' },
      { icon: 'hand', label: 'Facile à étaler' },
      { icon: 'sun', label: 'Usage quotidien' },
    ],
    ingredients: [
      'Collagène (selon le nom du produit)',
      "Liste INCI complète : à reprendre de l'emballage officiel",
    ],
    usage: [
      'Après le tonique, verser une petite quantité dans la paume.',
      'Appliquer sur le visage et le cou.',
      'Faire pénétrer par légers tapotements.',
    ],
    benefits: [
      'Texture émulsion légère',
      'Se superpose facilement aux autres soins',
      'Étape simple de la routine coréenne',
    ],
    skinTypes: "À confirmer selon la fiche officielle du produit.",
  },
];

