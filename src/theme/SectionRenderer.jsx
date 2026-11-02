import HeroSection from '../components/HeroSection.jsx';
import RitualSection from '../components/RitualSection.jsx';
import IngredientsSection from '../components/IngredientsSection.jsx';
import BeautyBanner from '../components/BeautyBanner.jsx';
import ProductCollection from '../components/ProductCollection.jsx';
import ImageWithText from '../components/ImageWithText.jsx';
import Reassurance from '../components/Reassurance.jsx';
import Testimonials from '../components/Testimonials.jsx';
import NewsletterSection from '../components/NewsletterSection.jsx';
import { useTheme } from './ThemeContext.jsx';

/**
 * Registre des sections de l'accueil : type du thème → VRAI composant de la boutique.
 * Ajouter une section = un schéma dans shared/theme/schema.json + une entrée ici.
 */
export const SECTION_COMPONENTS = {
  hero: HeroSection,
  featured_products: RitualSection,
  ingredients: IngredientsSection,
  promo_banner: BeautyBanner,
  product_collection: ProductCollection,
  image_with_text: ImageWithText,
  benefits: Reassurance,
  testimonials: Testimonials,
  newsletter: NewsletterSection,
};

export default function SectionRenderer({ sections }) {
  const { preview } = useTheme();
  return sections
    .filter((s) => !s.disabled && SECTION_COMPONENTS[s.type])
    .map((s) => {
      const Component = SECTION_COMPONENTS[s.type];
      // Aperçu de l'éditeur seulement : repère cliquable pour sélectionner la section.
      return preview
        ? <div key={s.id} className="theme-preview-section" data-theme-section={s.id}><Component section={s} /></div>
        : <Component key={s.id} section={s} />;
    });
}
