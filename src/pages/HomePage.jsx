import { Link } from 'react-router-dom';
import { ArrowDown, ArrowRight } from 'lucide-react';
import Header from '../components/Header.jsx';
import SiteFooter from '../components/SiteFooter.jsx';
import { PRODUCTS, CATALOG_IS_PLACEHOLDER } from '../data/products.js';
import IngredientsSection from '../components/IngredientsSection.jsx';
import RitualSection from '../components/RitualSection.jsx';
import BeautyBanner from '../components/BeautyBanner.jsx';
import ProductCarousel from '../components/ProductCarousel.jsx';
import Reassurance from '../components/Reassurance.jsx';
import Reveal from '../components/Reveal.jsx';
import heroImg from '../assets/hero/nature-hero-products.webp';
import heroImg640 from '../assets/hero/nature-hero-products-640.webp';
import heroWide from '../assets/hero/nature-hero-products-wide.webp';
import heroWide1280 from '../assets/hero/nature-hero-products-wide-1280.webp';

// Défilement fluide vers la collection (fonctionne aussi si l'URL contient déjà #collection).
function scrollToCollection(e) {
  const target = document.getElementById('collection');
  if (!target) return;
  e.preventDefault();
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  target.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
  window.history.replaceState(window.history.state, '', '#collection');
}

export default function HomePage() {

  return (
    <>
      <Header />
      <main>
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero__inner">
            <div className="hero__copy">
              <p className="eyebrow">La beauté au naturel</p>
              <h1 id="hero-title">Des soins doux pour une peau plus belle chaque jour</h1>
              <p className="hero__text">
                Une sélection de soins naturels pour une peau saine, lumineuse et harmonieuse.
              </p>
              <Link to={{ hash: '#collection' }} className="btn btn--primary btn--lg" onClick={scrollToCollection}>
                Découvrir nos produits <ArrowDown size={17} />
              </Link>
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
                  alt="Les cinq soins de la boutique sur des socles en pierre : gel Baroness Aloe Vera, crème SOME BY MI Yuja Niacin, émulsion ORJENA Power Collagen, patchs BIOVÈNE et crème Quret Vitamin Collagen"
                  fetchpriority="high"
                  decoding="async"
                />
              </picture>
            </div>
          </div>
        </section>

        <RitualSection />
        <IngredientsSection />
        <BeautyBanner />

        <section className="home-section moment" id="collection" aria-labelledby="collection-title">
          <div className="container">
            <Reveal as="header" className="section-head section-head--split">
              <div>
                <p className="eyebrow">Nos essentiels</p>
                <h2 className="section-title" id="collection-title">Les produits du moment</h2>
                <p className="section-intro">Découvrez nos {PRODUCTS.length} soins pour une routine simple et douce au quotidien.</p>
              </div>
              <Link to="/produits" className="text-arrow">Voir tout <ArrowRight size={16} aria-hidden="true" /></Link>
            </Reveal>
            <Reveal>
              <ProductCarousel products={PRODUCTS} label="Les produits du moment" />
            </Reveal>
            {CATALOG_IS_PLACEHOLDER && <p className="demo-note">Prix provisoires — à confirmer avant la mise en ligne.</p>}
          </div>
        </section>

        <Reassurance />
      </main>
      <SiteFooter />
    </>
  );
}
