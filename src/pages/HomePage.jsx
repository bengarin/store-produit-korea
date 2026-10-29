import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowDown } from 'lucide-react';
import Header from '../components/Header.jsx';
import TrustBar from '../components/TrustBar.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import ProductGrid, { CategoryChips } from '../components/ProductGrid.jsx';
import { PRODUCTS, CATALOG_IS_PLACEHOLDER } from '../data/products.js';
import heroImg from '../assets/hero/nature-hero-products.webp';
import heroImg640 from '../assets/hero/nature-hero-products-640.webp';
import heroWide from '../assets/hero/nature-hero-products-wide.webp';
import heroWide1280 from '../assets/hero/nature-hero-products-wide-1280.webp';

export default function HomePage() {
  const [category, setCategory] = useState('all');

  return (
    <>
      <Header />
      <main>
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero__inner">
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
            {/* Visuel produit fourni : image entière, jamais étirée ; seul le mur vide du haut se fond dans le crème. */}
            <div className="hero__visual">
              <picture>
                {/* Desktop (≥ 1000 px) : visuel paysage fourni ; mobile : visuel portrait inchangé. */}
                <source
                  media="(min-width: 1000px)"
                  srcSet={`${heroWide1280} 1280w, ${heroWide} 1672w`}
                  sizes="min(100vw, 1600px)"
                  width="1672"
                  height="941"
                />
                <img
                  src={heroImg}
                  srcSet={`${heroImg640} 640w, ${heroImg} 941w`}
                  sizes="(min-width: 900px) 46vw, (min-width: 600px) 520px, 100vw"
                  width="941"
                  height="1672"
                  alt="Les cinq soins NATURÉ sur des socles en pierre : gel Baroness Aloe Vera, crème SOME BY MI Yuja Niacin, émulsion ORJENA Power Collagen, patchs BIOVÈNE et crème Quret Vitamin Collagen"
                  fetchpriority="high"
                  decoding="async"
                />
              </picture>
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
            <p className="demo-note">Prix provisoires — à confirmer avant la mise en ligne.</p>
          )}
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
