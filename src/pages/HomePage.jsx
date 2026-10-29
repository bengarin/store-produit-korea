import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowDown } from 'lucide-react';
import Header from '../components/Header.jsx';
import TrustBar from '../components/TrustBar.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import ProductGrid, { CategoryChips } from '../components/ProductGrid.jsx';
import { PRODUCTS, CATALOG_IS_PLACEHOLDER } from '../data/products.js';
import heroPortrait from '../assets/backgrounds/podium-portrait.webp';
import heroWide from '../assets/backgrounds/podium-wide.webp';

// Ordre d'affichage sur le podium (de l'arrière vers l'avant).
const STAGE = [
  ['some-by-mi-yuja-niacin-cream', 'p-yuja'],
  ['orjena-power-collagen-emulsion', 'p-orjena'],
  ['baroness-aloe-vera-gel', 'p-aloe'],
  ['vitamin-collagen-vital-cream', 'p-vitamin'],
  ['biovene-eye-patches', 'p-biovene'],
];

export default function HomePage() {
  const [category, setCategory] = useState('all');

  return (
    <>
      <Header />
      <main>
        <section className="hero" aria-labelledby="hero-title">
          {/* Le média garde le ratio exact de la photo : les produits restent alignés sur le podium. */}
          <div className="hero__media" aria-hidden="true">
            <picture>
              <source media="(min-width: 700px)" srcSet={heroWide} width="1672" height="941" />
              <img className="hero__bg" src={heroPortrait} alt="" width="941" height="1672" fetchpriority="high" />
            </picture>
            {STAGE.map(([id, cls]) => {
              const p = PRODUCTS.find((x) => x.id === id);
              return p ? <img key={id} className={`hero__product ${cls}`} src={p.images[0].src} alt="" width="480" height="480" /> : null;
            })}
          </div>
          <div className="hero__content container">
            <div className="hero__copy">
              <p className="eyebrow">Révélez votre éclat naturel</p>
              <h1 id="hero-title">Des soins doux pour une peau plus belle chaque jour</h1>
              <p className="hero__text">
                Une sélection de soins coréens et naturels pour une peau saine, hydratée et lumineuse.
              </p>
              <Link to={{ hash: '#collection' }} className="btn btn--primary btn--lg">
                Découvrir nos produits <ArrowDown size={17} />
              </Link>
              <TrustBar className="trust--hero" />
            </div>
          </div>
        </section>

        <TrustBar className="trust--band" />

        <section className="section container" id="collection" aria-labelledby="collection-title">
          <div className="section-head">
            <div>
              <p className="eyebrow">Notre collection</p>
              <h2 className="section-title" id="collection-title">Nos produits</h2>
              <p className="section-intro">Découvrez nos {PRODUCTS.length} soins essentiels pour une peau saine et éclatante.</p>
            </div>
            <CategoryChips value={category} onChange={setCategory} />
          </div>
          <ProductGrid category={category} />
          {CATALOG_IS_PLACEHOLDER && (
            <p className="demo-note">Visuels et prix temporaires — à remplacer par les photos et tarifs officiels.</p>
          )}
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
