/**
 * 📷 PHOTOS PRODUITS — une seule source de vérité.
 *
 * Chaque produit a la même structure :
 *  - cardImage     : packshot net, utilisé dans les cartes, le panier, le récapitulatif
 *  - mainImage     : première image de la fiche produit
 *  - galleryImages : toutes les images de la fiche (la 1re = mainImage)
 *
 * `fit` :
 *  - 'contain' → packshot sur fond blanc, posé sur fond crème (rien n'est rogné)
 *  - 'cover'   → photo d'ambiance / texture / application, remplit le cadre
 *
 * Ajouter un produit : créer src/assets/products/<id>/, importer ses fichiers ici,
 * puis ajouter une entrée avec la même structure.
 */

// Baroness Aloe Vera Soothing Gel
import aloePackshot from '../assets/products/baroness-aloe-vera-gel/packshot.webp';
import aloeSplash from '../assets/products/baroness-aloe-vera-gel/splash.webp';
import aloeInHand from '../assets/products/baroness-aloe-vera-gel/in-hand.webp';
// SOME BY MI Yuja Niacin Anti Blemish Cream
import yujaPackshot from '../assets/products/some-by-mi-yuja-niacin-cream/packshot.webp';
import yujaLifestyle from '../assets/products/some-by-mi-yuja-niacin-cream/lifestyle.webp';
import yujaTexture from '../assets/products/some-by-mi-yuja-niacin-cream/texture.webp';
import yujaInUse from '../assets/products/some-by-mi-yuja-niacin-cream/in-use.webp';
// BIOVÈNE Tripeptide Cucumber Age-Defy Under Eye Patches
import bioPackshot from '../assets/products/biovene-eye-patches/packshot.webp';
import bioTexture from '../assets/products/biovene-eye-patches/texture.webp';
import bioBox from '../assets/products/biovene-eye-patches/box.webp';
import bioLifestyle from '../assets/products/biovene-eye-patches/lifestyle.webp';
import bioLifestyleBox from '../assets/products/biovene-eye-patches/lifestyle-box.webp';
// Quret Vitamin Collagen Vital Cream
import vitPackshot from '../assets/products/vitamin-collagen-vital-cream/packshot.webp';
import vitSetBox from '../assets/products/vitamin-collagen-vital-cream/set-box.webp';
import vitTube from '../assets/products/vitamin-collagen-vital-cream/tube.webp';
import vitTubeBox from '../assets/products/vitamin-collagen-vital-cream/tube-box.webp';
// ORJENA Power Collagen Emulsion
import orjPackshot from '../assets/products/orjena-power-collagen-emulsion/packshot.webp';
import orjBox from '../assets/products/orjena-power-collagen-emulsion/box.webp';
import orjInHand from '../assets/products/orjena-power-collagen-emulsion/in-hand.webp';

const img = (src, alt, kind, fit = 'contain') => ({ src, alt, kind, fit });

function entry(gallery) {
  return { cardImage: gallery[0], mainImage: gallery[0], galleryImages: gallery };
}

export const PRODUCT_IMAGES = {
  'baroness-aloe-vera-gel': entry(
    [
      img(aloePackshot, 'Pot Baroness Aloe Vera Soothing Gel, vue de face', 'packshot'),
      img(aloeSplash, 'Pot Baroness Aloe Vera entouré de feuilles d’aloe vera', 'ingredient'),
      img(aloeInHand, 'Pot Baroness Aloe Vera Soothing Gel tenu en main', 'in-hand', 'cover'),
    ],
  ),
  'some-by-mi-yuja-niacin-cream': entry(
    [
      img(yujaPackshot, 'Pot SOME BY MI Yuja Niacin Anti Blemish Cream, vue de face', 'packshot'),
      img(yujaLifestyle, 'Crème SOME BY MI Yuja Niacin avec des tranches de yuja', 'lifestyle', 'cover'),
      img(yujaTexture, 'Texture de la crème SOME BY MI Yuja Niacin', 'texture', 'cover'),
      img(yujaInUse, 'Application de la crème SOME BY MI Yuja Niacin sur la joue', 'in-use', 'cover'),
    ],
  ),
  'biovene-eye-patches': entry(
    [
      img(bioPackshot, 'Pot de patchs yeux BIOVÈNE Age-Defy avec spatule', 'packshot'),
      img(bioTexture, 'Patchs yeux BIOVÈNE vus de dessus dans leur pot', 'texture'),
      img(bioBox, 'Boîte des patchs BIOVÈNE Tripeptide Cucumber Under Eye Patches', 'packaging'),
      img(bioLifestyle, 'Pot de patchs BIOVÈNE ouvert avec des rondelles de concombre', 'lifestyle', 'cover'),
      img(bioLifestyleBox, 'Pot et boîte BIOVÈNE avec des rondelles de concombre', 'lifestyle', 'cover'),
    ],
  ),
  'vitamin-collagen-vital-cream': entry(
    [
      img(vitPackshot, 'Pot Quret Vitamin Collagen Vital Cream et son tube', 'packshot'),
      img(vitSetBox, 'Coffret Quret Vitamin Collagen Vital Cream avec pot et tube', 'packaging'),
      img(vitTube, 'Tube Quret Vitamin Collagen Vital Cream', 'packshot'),
      img(vitTubeBox, 'Tube Quret Vitamin Collagen Vital Cream et sa boîte', 'packaging'),
    ],
  ),
  'orjena-power-collagen-emulsion': entry(
    [
      img(orjPackshot, 'Flacon ORJENA Power Collagen Emulsion, vue de face', 'packshot'),
      img(orjBox, 'Flacon ORJENA Power Collagen Emulsion et sa boîte', 'packaging'),
      img(orjInHand, 'Flacon ORJENA Power Collagen Emulsion tenu en main', 'in-hand'),
    ],
  ),
};
