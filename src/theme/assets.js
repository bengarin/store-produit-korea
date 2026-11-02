/**
 * Images intégrées au site (les visuels actuels), référencées dans le thème par une clé fixe
 * ({ "asset": "hero-wide" }) ; les nouvelles images viennent de la médiathèque ({ "mediaId": 12 }).
 * Attributs identiques à ceux d'avant le thème : rendu inchangé.
 */
import heroImg from '../assets/hero/nature-hero-products.webp';
import heroImg640 from '../assets/hero/nature-hero-products-640.webp';
import heroWide from '../assets/hero/nature-hero-products-wide.webp';
import heroWide1280 from '../assets/hero/nature-hero-products-wide-1280.webp';
import bannerDesktop from '../assets/banner/eclat-desktop.webp';
import bannerDesktop1200 from '../assets/banner/eclat-desktop-1200.webp';
import bannerMobile from '../assets/banner/eclat-mobile.webp';
import bannerMobile640 from '../assets/banner/eclat-mobile-640.webp';

export const ASSETS = {
  'hero-wide': { src: heroWide, srcSet: `${heroWide1280} 1280w, ${heroWide} 1672w`, width: 1672, height: 941 },
  'hero-portrait': { src: heroImg, srcSet: `${heroImg640} 640w, ${heroImg} 941w`, width: 941, height: 1672 },
  'banner-desktop': { src: bannerDesktop, srcSet: `${bannerDesktop1200} 1200w, ${bannerDesktop} 1920w`, width: 1920, height: 768 },
  'banner-mobile': { src: bannerMobile640, srcSet: `${bannerMobile640} 640w, ${bannerMobile} 890w`, width: 890, height: 1767 },
};

/** Libellés des images intégrées (éditeur). */
export const ASSET_LABELS = {
  'hero-wide': 'Visuel d’origine (paysage)',
  'hero-portrait': 'Visuel d’origine (portrait)',
  'banner-desktop': 'Visuel d’origine (paysage)',
  'banner-mobile': 'Visuel d’origine (portrait)',
};

/**
 * Valeur d'image du thème → { src, srcSet, width, height } ou null.
 * `media` = { [id]: { src, src640, width, height } } fourni par l'API avec le thème.
 */
export function resolveImage(value, media = {}) {
  if (!value) return null;
  if (value.asset) return ASSETS[value.asset] || null;
  const m = value.mediaId && media[value.mediaId];
  if (!m) return null;
  return {
    src: m.src,
    srcSet: m.src640 ? `${m.src640} 640w, ${m.src} ${m.width}w` : undefined,
    width: m.width,
    height: m.height,
  };
}
