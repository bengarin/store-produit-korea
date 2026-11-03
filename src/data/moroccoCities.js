/**
 * Villes du Maroc proposées au checkout (nom français = valeur envoyée au serveur, nom arabe = affichage en arabe).
 * Orthographe française identique aux villes déjà configurées (zones de livraison, données de démo) pour que les
 * tarifs par ville continuent de s'appliquer. Les villes ajoutées dans l'administration sont aussi proposées.
 */
export const MOROCCO_CITIES = [
  ['Agadir', 'أكادير'], ['Aït Melloul', 'أيت ملول'], ['Al Hoceïma', 'الحسيمة'], ['Asilah', 'أصيلة'],
  ['Azilal', 'أزيلال'], ['Azrou', 'أزرو'], ['Ben Guerir', 'بن جرير'], ['Béni Mellal', 'بني ملال'],
  ['Benslimane', 'بنسليمان'], ['Berkane', 'بركان'], ['Berrechid', 'برشيد'], ['Boujdour', 'بوجدور'],
  ['Bouznika', 'بوزنيقة'], ['Casablanca', 'الدار البيضاء'], ['Chefchaouen', 'شفشاون'], ['Chichaoua', 'شيشاوة'],
  ['Dakhla', 'الداخلة'], ['Driouch', 'الدريوش'], ['El Jadida', 'الجديدة'], ['El Kelâa des Sraghna', 'قلعة السراغنة'],
  ['Errachidia', 'الرشيدية'], ['Essaouira', 'الصويرة'], ['Fès', 'فاس'], ['Fnideq', 'الفنيدق'],
  ['Fquih Ben Salah', 'الفقيه بن صالح'], ['Guelmim', 'كلميم'], ['Guercif', 'جرسيف'], ['Ifrane', 'إفران'],
  ['Inezgane', 'إنزكان'], ['Jerada', 'جرادة'], ['Kénitra', 'القنيطرة'], ['Khémisset', 'الخميسات'],
  ['Khénifra', 'خنيفرة'], ['Khouribga', 'خريبكة'], ['Ksar El Kebir', 'القصر الكبير'], ['Laâyoune', 'العيون'],
  ['Larache', 'العرائش'], ["M'diq", 'المضيق'], ['Marrakech', 'مراكش'], ['Martil', 'مرتيل'],
  ['Meknès', 'مكناس'], ['Midelt', 'ميدلت'], ['Mohammedia', 'المحمدية'], ['Nador', 'الناظور'],
  ['Ouarzazate', 'ورزازات'], ['Ouazzane', 'وزان'], ['Oujda', 'وجدة'], ['Rabat', 'الرباط'],
  ['Safi', 'آسفي'], ['Salé', 'سلا'], ['Sefrou', 'صفرو'], ['Settat', 'سطات'],
  ['Sidi Bennour', 'سيدي بنور'], ['Sidi Ifni', 'سيدي إفني'], ['Sidi Kacem', 'سيدي قاسم'], ['Sidi Slimane', 'سيدي سليمان'],
  ['Skhirat', 'الصخيرات'], ['Smara', 'السمارة'], ['Souk El Arbaa', 'سوق الأربعاء الغرب'], ['Tan-Tan', 'طانطان'],
  ['Tanger', 'طنجة'], ['Taounate', 'تاونات'], ['Taourirt', 'تاوريرت'], ['Taroudant', 'تارودانت'],
  ['Taza', 'تازة'], ['Témara', 'تمارة'], ['Tétouan', 'تطوان'], ['Tiflet', 'تيفلت'],
  ['Tinghir', 'تنغير'], ['Tiznit', 'تيزنيت'], ['Youssoufia', 'اليوسفية'], ['Zagora', 'زاكورة'],
];

/** Nom arabe d'une ville (clé : nom français). */
export const CITY_AR_NAMES = Object.fromEntries(MOROCCO_CITIES);

/** Valeur spéciale de la liste : la ville est saisie à la main. */
export const OTHER_CITY = 'autre';

/** Saisie libre acceptée : lettres latines (accents compris) ou arabes, espaces, apostrophe, tiret (même règle que le serveur). */
export const FREE_CITY = /^[A-Za-zÀ-ÿ؀-ۿ' -]{2,80}$/;

/** Texte simplifié pour la recherche : minuscules, sans accents latins ni signes arabes, alef unifié. */
export function searchKey(text) {
  return (text || '')
    .normalize('NFD')
    .replace(/[̀-ًͯ-ْـ]/g, '')
    .replace(/[أإآ]/g, 'ا')
    .toLowerCase()
    .trim();
}

/**
 * Villes proposées : liste nationale + villes configurées dans l'administration (sans doublon),
 * triées selon la langue d'affichage.
 */
export function cityOptions(configured = [], lang = 'fr') {
  const names = new Map(MOROCCO_CITIES.map(([fr]) => [searchKey(fr), fr]));
  configured.forEach((c) => { if (!names.has(searchKey(c))) names.set(searchKey(c), c); });
  const label = (fr) => (lang === 'ar' ? CITY_AR_NAMES[fr] || fr : fr);
  return [...names.values()]
    .map((value) => ({ value, label: label(value), key: `${searchKey(value)} ${searchKey(CITY_AR_NAMES[value] || '')}` }))
    .sort((a, b) => a.label.localeCompare(b.label, lang));
}
