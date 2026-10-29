/**
 * 🌿 LE RITUEL NATURÉ — 3 étapes, chacune reliée à un produit RÉEL du catalogue.
 * - productId : id dans src/data/products.js
 * - imageKind : quelle photo de la galerie du produit utiliser (voir productImages.js)
 * - imagePosition : cadrage de la photo dans la carte (object-position)
 * Textes volontairement descriptifs : aucune promesse de résultat.
 */
export const RITUAL_STEPS = [
  {
    step: 1,
    title: 'Nettoyer & préparer',
    text: 'Après votre nettoyant habituel, une touche de fraîcheur pour préparer la peau.',
    productId: 'baroness-aloe-vera-gel',
    imageKind: 'in-hand',
    imagePosition: '50% 45%',
  },
  {
    step: 2,
    title: 'Hydrater',
    text: 'Une crème au yuja et à la niacinamide pour poursuivre votre routine.',
    productId: 'some-by-mi-yuja-niacin-cream',
    imageKind: 'lifestyle',
    imagePosition: '50% 88%',
  },
  {
    step: 3,
    title: 'Sublimer',
    text: 'Un moment dédié au contour des yeux pour terminer votre rituel.',
    productId: 'biovene-eye-patches',
    imageKind: 'lifestyle',
    imagePosition: '50% 40%',
  },
];
