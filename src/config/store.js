/**
 * ⚙️ CONFIGURATION DE LA BOUTIQUE — tout ce qui se change souvent est ICI.
 *
 * Valeurs marquées [DÉMO] = à remplacer par vos vraies règles business.
 */
export const STORE_CONFIG = {
  brandName: 'Ma Petite Corée',
  brandTagline: 'KOREAN & NATURAL SKINCARE',

  /** Devise affichée après les prix. */
  currencyLabel: 'DH',

  /** [DÉMO] Frais de livraison à domicile, en DH. */
  deliveryFee: 20,

  /**
   * [DÉMO] Livraison offerte à partir de ce sous-total (en DH).
   * Mettre `null` pour désactiver.
   */
  freeDeliveryThreshold: null,

  /**
   * Numéro WhatsApp de la boutique, format international SANS "+" ni espaces.
   * Exemple de format : '2126XXXXXXXX'. Laisser '' tant qu'il n'est pas configuré.
   */
  whatsappNumber: '',

  /**
   * [DÉMO] Codes promo acceptés : CODE → pourcentage de remise.
   * Supprimez ou remplacez ce code avant la mise en ligne.
   */
  promoCodes: {
    NATURE10: 10,
  },

  /** Villes proposées dans le formulaire de commande. */
  cities: [
    'Casablanca', 'Rabat', 'Marrakech', 'Fès', 'Tanger', 'Agadir', 'Meknès',
    'Oujda', 'Kénitra', 'Tétouan', 'Salé', 'Témara', 'Mohammedia', 'El Jadida',
    'Safi', 'Béni Mellal', 'Nador', 'Khouribga', 'Settat', 'Laâyoune',
  ],
};
