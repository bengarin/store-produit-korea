import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import HomeEssentials from '../components/HomeEssentials.jsx';
import HeroCarousel from '../components/HeroCarousel.jsx';
import SectionRenderer from '../theme/SectionRenderer.jsx';
import { useTheme } from '../theme/ThemeContext.jsx';

/**
 * Accueil, dans cet ordre :
 * 1. la bannière principale — diapositives publiées dans Admin → Visuels marketing (fixe s'il y en a une,
 *    carrousel s'il y en a plusieurs) ; sans diapositives transmises (mode démo, aperçu du thème) : section « hero » du thème ;
 * 2. « Nos collections » (onglets des collections + produits) ;
 * 3. la 1re section « produits » du thème (Produits tendance) ;
 * 4. les autres sections du thème, dans leur ordre.
 */
export default function HomePage() {
  const { theme, heroSlides } = useTheme();
  const visible = theme.home.filter((s) => !s.disabled);
  const useSlides = Array.isArray(heroSlides);
  const themeHero = !useSlides && visible[0]?.type === 'hero' ? [visible[0]] : [];
  const rest = visible.filter((s) => (useSlides ? s.type !== 'hero' : s !== themeHero[0]));
  const trending = rest.find((s) => s.type === 'product_collection');
  const others = rest.filter((s) => s !== trending);
  return (
    <>
      <Header />
      <main>
        {useSlides ? <HeroCarousel slides={heroSlides} /> : <SectionRenderer sections={themeHero} />}
        <HomeEssentials />
        {trending && <SectionRenderer sections={[trending]} />}
        <SectionRenderer sections={others} />
      </main>
      <SiteFooter />
    </>
  );
}
