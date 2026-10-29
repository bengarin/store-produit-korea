/**
 * 🌿 INGRÉDIENTS À L'HONNEUR
 *
 * - productIds : produits RÉELS du catalogue (src/data/products.js) qui contiennent
 *   l'ingrédient d'après leur nom. Laisser [] si aucun produit n'est encore associé :
 *   la carte affichera « Soins bientôt disponibles » sans lien.
 * - focus : point de cadrage horizontal de la photo dans la carte (0 % = gauche, 100 % = droite).
 * - tagline : 2-3 mots affichés sous le nom ; description : phrase complète (page produits filtrée).
 * - Textes : descriptifs d'ambiance, sans promesse d'efficacité.
 */
import aloe from '../assets/ingredients/aloe-vera.webp';
import aloe640 from '../assets/ingredients/aloe-vera-640.webp';
import yuja from '../assets/ingredients/yuja.webp';
import yuja640 from '../assets/ingredients/yuja-640.webp';
import concombre from '../assets/ingredients/concombre.webp';
import concombre640 from '../assets/ingredients/concombre-640.webp';
import collagene from '../assets/ingredients/collagene.webp';
import collagene640 from '../assets/ingredients/collagene-640.webp';
import { getProductById } from './products.js';

export const INGREDIENTS = [
  {
    id: 'aloe-vera',
    tagline: 'Fraîcheur végétale',
    name: 'Aloe Vera',
    description: 'Une touche de fraîcheur pour votre routine quotidienne.',
    productsTitle: 'Les soins à l’Aloe Vera',
    image: { src: aloe, src640: aloe640, alt: 'Feuilles d’aloe vera fraîchement coupées et gel transparent dans une coupelle', focus: '42%' },
    productIds: ['baroness-aloe-vera-gel'],
  },
  {
    id: 'yuja',
    tagline: 'Agrume coréen',
    name: 'Yuja',
    description: 'Un ingrédient apprécié dans les routines dédiées à l’éclat du teint.',
    productsTitle: 'Les soins au Yuja',
    image: { src: yuja, src640: yuja640, alt: 'Fruits de yuja entiers et coupés sur une pierre claire', focus: '45%' },
    productIds: ['some-by-mi-yuja-niacin-cream'],
  },
  {
    id: 'concombre',
    tagline: 'Fraîcheur légère',
    name: 'Concombre',
    description: 'Une sensation de fraîcheur pour un moment de soin agréable.',
    productsTitle: 'Les soins au concombre',
    image: { src: concombre, src640: concombre640, alt: 'Rondelles de concombre frais avec des gouttes d’eau', focus: '42%' },
    productIds: ['biovene-eye-patches'],
  },
  {
    id: 'collagene',
    tagline: 'Soin confort',
    name: 'Collagène',
    description: 'Un ingrédient présent dans les soins dédiés au confort et à l’apparence de la peau.',
    productsTitle: 'Les soins au collagène',
    image: { src: collagene, src640: collagene640, alt: 'Crème onctueuse dans une coupelle en verre, entourée de feuilles et de sphères transparentes', focus: '50%' },
    productIds: ['vitamin-collagen-vital-cream', 'orjena-power-collagen-emulsion'],
  },
];

// Garde uniquement les produits qui existent vraiment dans le catalogue.
INGREDIENTS.forEach((ing) => {
  ing.productIds = ing.productIds.filter((id) => getProductById(id));
});

export const getIngredientById = (id) => INGREDIENTS.find((i) => i.id === id);
