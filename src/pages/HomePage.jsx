import { Link } from 'react-router-dom';
import { ArrowDown } from 'lucide-react';
import Header from '../components/Header.jsx';
import TrustBar from '../components/TrustBar.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import { PRODUCTS } from '../data/products.js';
import heroPortrait from '../assets/backgrounds/podium-portrait.webp';
import heroWide from '../assets/backgrounds/podium-wide.webp';

// Ordre d'affichage sur le podium (de l'arrière vers l'avant).
const STAGE = [
  { id: 'orjena-power-collagen-emulsion', cls: 'p-orjena' },
  { id: 'some-by-mi-yuja-niacin-cream', cls: 'p-yuja' },
  { id: 'baroness-aloe-vera-gel', cls: 'p-aloe' },
  { id: 'vitamin-collagen-vital-cream', cls: 'p-vitamin' },
  { id: 'biovene-eye-patches', cls: 'p-biovene' },
];

export default function HomePage() {
  return (
    <>
      <Header />
      <main>
        <section className="hero" aria-labelledby="hero-title">
          <picture>
            <source media="(min-width: 700px)" srcSet={heroWide} />
            <img className="hero__bg" src={heroPortrait} alt="" fetchpriority="high" />
          </picture>
          <div className="hero__content">
            <p className="eyebrow">Révélez votre éclat naturel</p>
            <h1 id="hero-title">Des soins doux pour une peau plus belle chaque jour</h1>
            <p className="hero__text">
              Une sélection de soins coréens et naturels pour une peau saine, hydratée et lumineuse.
            </p>
            <Link to="/produits" className="btn btn--primary btn--lg">
              Découvrir nos produits <ArrowDown size={18} />
            </Link>
          </div>
          <div className="hero__stage" aria-hidden="true">
            {STAGE.map(({ id, cls }) => {
              const p = PRODUCTS.find((x) => x.id === id);
              return p ? <img key={id} className={`hero__product ${cls}`} src={p.images[0].src} alt="" /> : null;
            })}
          </div>
        </section>
        <TrustBar />
      </main>
      <SiteFooter />
    </>
  );
}
