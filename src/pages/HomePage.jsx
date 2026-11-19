import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import HomeEssentials from '../components/HomeEssentials.jsx';
import SectionRenderer from '../theme/SectionRenderer.jsx';
import { useTheme } from '../theme/ThemeContext.jsx';

/**
 * Accueil : sections du thème publié (thème par défaut = accueil d'origine).
 * « Nos essentiels » (onglets des collections + produits) s'insère juste après la bannière principale
 * (ou en tête s'il n'y en a pas).
 */
export default function HomePage() {
  const { theme } = useTheme();
  const sections = theme.home;
  const firstVisible = sections.findIndex((s) => !s.disabled);
  const split = firstVisible >= 0 && sections[firstVisible].type === 'hero' ? firstVisible + 1 : 0;
  return (
    <>
      <Header />
      <main>
        <SectionRenderer sections={sections.slice(0, split)} />
        <HomeEssentials />
        <SectionRenderer sections={sections.slice(split)} />
      </main>
      <SiteFooter />
    </>
  );
}
