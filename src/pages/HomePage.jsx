import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import SectionRenderer from '../theme/SectionRenderer.jsx';
import { useTheme } from '../theme/ThemeContext.jsx';

/** Accueil : sections du thème publié (thème par défaut = accueil d'origine). */
export default function HomePage() {
  const { theme } = useTheme();
  return (
    <>
      <Header />
      <main>
        <SectionRenderer sections={theme.home} />
      </main>
      <SiteFooter />
    </>
  );
}
