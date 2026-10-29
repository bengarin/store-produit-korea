/**
 * 🧴 CATALOGUE PRODUITS (données locales de démonstration)
 *
 * - Prix : valeurs PROVISOIRES [DÉMO] → modifiez `price` (en DH).
 * - Photos : remplacez les imports ci-dessous par vos vraies photos
 *   (déposez-les dans src/assets/products/, format .webp conseillé).
 * - Textes : contenu INDICATIF basé sur le nom du produit. À valider avec
 *   l'emballage / la fiche officielle de la marque avant la mise en ligne.
 *   Aucune allégation médicale ou dermatologique n'est faite ici.
 */
import { Droplets, Leaf, Sparkles, Sun, Citrus, Eye, Clock, Layers, FlaskConical, Hand } from 'lucide-react';

import aloeImg from '../assets/products/aloe-vera-gel.svg';
import yujaImg from '../assets/products/yuja-niacin-cream.svg';
import patchesImg from '../assets/products/eye-patches.svg';
import vitaminImg from '../assets/products/vitamin-collagen-cream.svg';
import orjenaImg from '../assets/products/collagen-emulsion.svg';

export const CATEGORIES = [
  { id: 'all', label: 'Tous' },
  { id: 'hydratation', label: 'Hydratation' },
  { id: 'anti-age', label: 'Anti-âge' },
  { id: 'eclat', label: 'Éclat' },
];

export const CATEGORY_LABELS = {
  hydratation: 'Hydratation',
  'anti-age': 'Anti-âge',
  eclat: 'Éclat',
};

/** true tant que les photos/prix/textes sont des valeurs de démonstration. */
export const CATALOG_IS_PLACEHOLDER = true;

export const PRODUCTS = [
  {
    id: 'baroness-aloe-vera-gel',
    brand: 'Baroness',
    name: 'Aloe Vera Soothing Gel',
    displayName: 'Baroness Aloe Vera Soothing Gel',
    price: 129, // [DÉMO]
    categories: ['hydratation'],
    tint: '#E4EEDB',
    images: [{ src: aloeImg, alt: 'Visuel provisoire du gel Baroness Aloe Vera' }],
    summary:
      "Gel à l'aloe vera à la texture fraîche et légère, pensé pour le visage et le corps.",
    highlights: [
      { icon: Leaf, label: "À l'aloe vera" },
      { icon: Droplets, label: 'Texture gel' },
      { icon: Hand, label: 'Visage & corps' },
      { icon: Sun, label: 'Usage quotidien' },
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
    brand: 'SOME BY MI',
    name: 'Yuja Niacin Anti Blemish Cream',
    displayName: 'SOME BY MI Yuja Niacin Cream',
    price: 199, // [DÉMO]
    categories: ['eclat'],
    tint: '#FBF0CF',
    images: [{ src: yujaImg, alt: 'Visuel provisoire de la crème SOME BY MI Yuja Niacin' }],
    summary:
      'Une crème formulée avec du Yuja (agrume coréen) et de la niacinamide, pour une routine axée sur l’éclat du teint.',
    highlights: [
      { icon: Citrus, label: 'Extrait de Yuja' },
      { icon: FlaskConical, label: 'Niacinamide' },
      { icon: Sparkles, label: 'Routine éclat' },
      { icon: Sun, label: 'Usage quotidien' },
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
    brand: 'BIOVÈNE',
    name: 'Tripeptide Cucumber Age-Defy Under Eye Patches',
    displayName: 'Biovène Eye Patches',
    price: 149, // [DÉMO]
    categories: ['anti-age'],
    tint: '#D8F1EF',
    images: [{ src: patchesImg, alt: 'Visuel provisoire des patchs yeux Biovène' }],
    summary:
      'Patchs pour le contour des yeux associant tripeptide et concombre, pour un moment de soin rapide.',
    highlights: [
      { icon: Eye, label: 'Contour des yeux' },
      { icon: FlaskConical, label: 'Tripeptide' },
      { icon: Leaf, label: 'Concombre' },
      { icon: Clock, label: 'Pose rapide' },
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
    brand: 'Vitamin Collagen',
    name: 'Vital Cream',
    displayName: 'Vitamin Collagen Vital Cream',
    price: 229, // [DÉMO]
    categories: ['anti-age', 'eclat'],
    tint: '#FBE3CF',
    images: [{ src: vitaminImg, alt: 'Visuel provisoire de la crème Vitamin Collagen' }],
    summary:
      'Crème associant vitamines et collagène, pour une routine de soin riche et confortable.',
    highlights: [
      { icon: Sparkles, label: 'Vitamines' },
      { icon: Layers, label: 'Collagène' },
      { icon: Droplets, label: 'Texture crème' },
      { icon: Sun, label: 'Matin & soir' },
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
    brand: 'ORJENA',
    name: 'Power Collagen Emulsion',
    displayName: 'ORJENA Power Collagen Emulsion',
    price: 179, // [DÉMO]
    categories: ['hydratation', 'anti-age'],
    tint: '#F1DDD8',
    images: [{ src: orjenaImg, alt: "Visuel provisoire de l'émulsion ORJENA Power Collagen" }],
    summary:
      'Émulsion fluide au collagène, à utiliser comme étape légère de la routine coréenne.',
    highlights: [
      { icon: Layers, label: 'Collagène' },
      { icon: Droplets, label: 'Texture fluide' },
      { icon: Hand, label: 'Facile à étaler' },
      { icon: Sun, label: 'Usage quotidien' },
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

export const getProductById = (id) => PRODUCTS.find((p) => p.id === id);
