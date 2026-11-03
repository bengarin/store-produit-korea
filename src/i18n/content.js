/**
 * Traduction des CONTENUS d'origine (thème par défaut, valeurs par défaut des sections, catégories, ingrédients).
 * Règle : un texte est traduit seulement s'il est EXACTEMENT le texte d'origine. Un texte modifié par l'équipe
 * dans l'administration est affiché tel quel (pas de traduction automatique ni inventée).
 * Les marques et noms de produits (Baroness, SOME BY MI, ORJENA, BIOVÈNE, Quret…) restent en caractères latins.
 * Les jetons {nombre} et {frais_livraison} sont conservés.
 */
import { CITY_AR_NAMES } from '../data/moroccoCities.js';

const AR = {
  // Barre d'annonce, menu, pied de page
  'Livraison partout au Maroc · Paiement à la livraison': 'التوصيل إلى جميع أنحاء المغرب · الدفع عند الاستلام',
  Accueil: 'الرئيسية',
  'Nos produits': 'منتجاتنا',
  Favoris: 'المفضلة',
  'Mon panier': 'سلة التسوق',
  'Notre histoire': 'قصتنا',
  'Nouveau lien': 'رابط جديد',

  // Bannière principale
  'La beauté au naturel': 'الجمال بطبيعته',
  'Des soins doux pour une peau plus belle chaque jour': 'عناية لطيفة لبشرة أجمل كل يوم',
  'Une sélection de soins naturels pour une peau saine, lumineuse et harmonieuse.': 'تشكيلة من منتجات العناية الطبيعية لبشرة صحية ومشرقة ومتوازنة.',
  'Découvrir nos produits': 'اكتشفوا منتجاتنا',
  'Les cinq soins de la boutique sur des socles en pierre : gel Baroness Aloe Vera, crème SOME BY MI Yuja Niacin, émulsion ORJENA Power Collagen, patchs BIOVÈNE et crème Quret Vitamin Collagen':
    'منتجات العناية الخمسة على قواعد حجرية: جل Baroness Aloe Vera، وكريم SOME BY MI Yuja Niacin، ومستحلب ORJENA Power Collagen، ولصقات BIOVÈNE، وكريم Quret Vitamin Collagen',

  // Rituel
  'Votre routine beauté': 'روتين جمالكم',
  'Le rituel NATURE': 'روتين NATURE',
  'Trois étapes simples, trois soins, une seule sélection.': 'ثلاث خطوات بسيطة، ثلاثة منتجات، وتشكيلة واحدة.',
  'Nettoyer & préparer': 'التنظيف والتحضير',
  'Après votre nettoyage quotidien, préparez votre peau en douceur.': 'بعد التنظيف اليومي، حضّروا بشرتكم بلطف.',
  Hydrater: 'الترطيب',
  'Une crème au yuja et à la niacinamide pour poursuivre votre routine.': 'كريم باليوجا والنياسيناميد لمواصلة روتينكم.',
  Sublimer: 'إبراز الجمال',
  'Un moment dédié au contour des yeux pour terminer votre rituel.': 'لحظة مخصّصة لمحيط العينين لإتمام روتينكم.',
  'Produits mis en avant': 'منتجات مختارة',

  // Ingrédients (section)
  'Nos ingrédients naturels': 'مكوّناتنا الطبيعية',
  'Des actifs choisis pour votre peau': 'مكوّنات فعّالة مختارة لبشرتكم',
  'Des ingrédients inspirés par la nature et les traditions de beauté coréennes.': 'مكوّنات مستوحاة من الطبيعة ومن تقاليد الجمال الكورية.',

  // Bannière promotionnelle
  'Tout en douceur': 'بكل لطف',
  'Révélez votre éclat naturel': 'أبرزوا إشراقتكم الطبيعية',
  'Des soins coréens et naturels pour accompagner votre routine, jour après jour.': 'منتجات عناية كورية وطبيعية ترافق روتينكم يومًا بعد يوم.',
  'Portrait d’une femme au teint lumineux, la main posée sur la joue': 'صورة امرأة ببشرة مشرقة تضع يدها على خدّها',

  // Collection
  'Nos essentiels': 'أساسياتنا',
  'Les produits du moment': 'منتجات اللحظة',
  'Découvrez nos {nombre} soins pour une routine simple et douce au quotidien.': 'اكتشفوا منتجات العناية لدينا ({nombre}) لروتين يومي بسيط ولطيف.',
  'Voir tout': 'عرض الكل',

  // Avantages
  'Paiement à la livraison': 'الدفع عند الاستلام',
  'Vous payez à la réception': 'الدفع عند استلام الطلب',
  'Produits authentiques': 'منتجات أصلية',
  'Marques coréennes sélectionnées': 'علامات كورية مختارة بعناية',
  'Livraison partout au Maroc': 'التوصيل إلى جميع أنحاء المغرب',
  'À domicile · {frais_livraison}': 'إلى باب المنزل · {frais_livraison}',
  'Service client': 'خدمة العملاء',
  'Chaque commande confirmée par téléphone': 'نؤكد كل طلب عبر الهاتف',

  // Valeurs par défaut des sections ajoutées depuis l'éditeur
  'Avis clients': 'آراء العملاء',
  'Elles nous font confiance': 'يثقون بنا',
  'Restez informée': 'ابقوا على اطّلاع',
  'Nouveautés et conseils de routine, sans excès.': 'جديدنا ونصائح للعناية، دون إزعاج.',
  "Je m'inscris": 'الاشتراك',
  "J'accepte de recevoir les e-mails de Ma Petite Corée. Je peux me désinscrire à tout moment.":
    'أوافق على تلقي الرسائل الإلكترونية من Ma Petite Corée، ويمكنني إلغاء الاشتراك في أي وقت.',
  'Votre titre': 'العنوان',
  'Votre message': 'الرسالة',

  // Catégories d'origine
  Hydratation: 'الترطيب',
  'Anti-âge': 'مكافحة علامات التقدم في السن',
  Éclat: 'الإشراق',

  // Ingrédients (données de la boutique)
  'Aloe Vera': 'الألوفيرا',
  Yuja: 'اليوجا',
  Concombre: 'الخيار',
  Collagène: 'الكولاجين',
  'Fraîcheur végétale': 'انتعاش نباتي',
  'Agrume coréen': 'حمضيات كورية',
  'Fraîcheur légère': 'انتعاش خفيف',
  'Soin confort': 'عناية مريحة',
  'Une touche de fraîcheur pour votre routine quotidienne.': 'لمسة من الانتعاش للروتين اليومي.',
  'Un ingrédient apprécié dans les routines dédiées à l’éclat du teint.': 'مكوّن محبّب في روتينات العناية بإشراقة البشرة.',
  'Une sensation de fraîcheur pour un moment de soin agréable.': 'إحساس بالانتعاش للحظة عناية ممتعة.',
  'Un ingrédient présent dans les soins dédiés au confort et à l’apparence de la peau.': 'مكوّن حاضر في منتجات العناية المخصّصة لراحة البشرة ومظهرها.',
  'Les soins à l’Aloe Vera': 'منتجات العناية بالألوفيرا',
  'Les soins au Yuja': 'منتجات العناية باليوجا',
  'Les soins au concombre': 'منتجات العناية بالخيار',
  'Les soins au collagène': 'منتجات العناية بالكولاجين',
  'Feuilles d’aloe vera fraîchement coupées et gel transparent dans une coupelle': 'أوراق ألوفيرا مقطوفة حديثًا وجل شفاف في وعاء صغير',
  'Fruits de yuja entiers et coupés sur une pierre claire': 'ثمار يوجا كاملة ومقطّعة على حجر فاتح',
  'Rondelles de concombre frais avec des gouttes d’eau': 'شرائح خيار طازج مع قطرات ماء',
  'Crème onctueuse dans une coupelle en verre, entourée de feuilles et de sphères transparentes': 'كريم ناعم في وعاء زجاجي تحيط به أوراق وكرات شفافة',
};

/** Villes du formulaire de commande : libellé arabe (la valeur envoyée au serveur reste inchangée). */
// Noms arabes des villes : une seule liste, src/data/moroccoCities.js.
export const CITY_AR = CITY_AR_NAMES;

const TABLES = { ar: { ...AR, ...CITY_AR } };

export function translateContent(lang, text) {
  if (typeof text !== 'string') return text;
  return TABLES[lang]?.[text] ?? text;
}
